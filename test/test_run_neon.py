# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os.path
import sys
import unittest

from time import time, sleep
from multiprocessing import Process
from neon_utils.log_utils import LOG
from mycroft_bus_client import MessageBusClient, Message
from neon_utils.configuration_utils import get_neon_local_config

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

AUDIO_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "audio_files")


class TestRunNeon(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Blacklist skills to prevent logged errors
        local_conf = get_neon_local_config()
        local_conf["skills"]["blacklist"] = \
            local_conf["skills"]["blacklist"].extend(
                ["skill-ovos-homescreen.openvoiceos",
                 "skill-balena-wifi-setup.openvoiceos"])
        local_conf.write_changes()

        from neon_core.run_neon import start_neon

        cls.process = Process(target=start_neon, daemon=False)
        cls.process.start()
        cls.bus = MessageBusClient()
        cls.bus.run_in_thread()
        cls.bus.connected_event.wait()
        cls.bus.wait_for_message("mycroft.ready", 600)

    @classmethod
    def tearDownClass(cls) -> None:
        from neon_core.run_neon import stop_neon

        try:
            cls.bus.emit(Message("neon.shutdown"))
            cls.bus.close()
            cls.process.join(30)
            if cls.process.is_alive():
                stop = Process(target=stop_neon, daemon=False)
                stop.start()
                stop.join(60)
                cls.process.join(15)
            if cls.process.is_alive:
                raise ChildProcessError("Process Not Killed!")
        except Exception as e:
            LOG.error(e)

    def test_messagebus_connection(self):
        from mycroft_bus_client import MessageBusClient
        bus = MessageBusClient()
        bus.run_in_thread()
        self.assertTrue(bus.started_running)
        bus.connected_event.wait(10)
        self.assertTrue(bus.connected_event.is_set())
        bus.close()

    def test_speech_module(self):
        # TODO: Remove this after readiness is better defined DM
        i = 0
        response = self.bus.wait_for_response(Message('mycroft.speech.is_ready'))
        while not response.data['status'] and i < 10:
            LOG.warning(f"Speech not ready when core reported ready!")
            sleep(5)
            response = self.bus.wait_for_response(Message('mycroft.speech.is_ready'))
            i += 1
        self.assertTrue(response.data['status'])

        context = {"client": "tester",
                   "ident": str(round(time())),
                   "user": "TestRunner"}
        stt_resp = self.bus.wait_for_response(Message("neon.get_stt",
                                                      {"audio_file": os.path.join(AUDIO_FILE_PATH, "stop.wav")},
                                                      context), context["ident"])
        self.assertEqual(stt_resp.context, context)
        self.assertIsInstance(stt_resp.data.get("parser_data"), dict)
        self.assertIsInstance(stt_resp.data.get("transcripts"), list)
        self.assertIn("stop", stt_resp.data.get("transcripts"))

    def test_audio_module(self):
        response = self.bus.wait_for_response(Message('mycroft.audio.is_ready'))
        self.assertTrue(response.data['status'])

        text = "This is a test"
        context = {"client": "tester",
                   "ident": str(time()),
                   "user": "TestRunner"}
        tts_resp = self.bus.wait_for_response(Message("neon.get_tts", {"text": text}, context),
                                              context["ident"], timeout=60)
        self.assertEqual(tts_resp.context, context)
        responses = tts_resp.data
        self.assertIsInstance(responses, dict)
        self.assertEqual(len(responses), 1)
        resp = list(responses.values())[0]
        self.assertIsInstance(resp, dict)
        self.assertEqual(resp.get("sentence"), text)

    # TODO: Define some generic enclosure events to test
    # def test_enclosure_module(self):
    #     resp = self.bus.wait_for_response(Message("mycroft.volume.get"))
    #     self.assertIsInstance(resp, Message)
    #     vol = resp.data.get("percent")
    #     mute = resp.data.get("muted")
    #
    #     self.assertIsInstance(vol, float)
    #     self.assertIsInstance(mute, bool)

    # TODO: Implement transcribe tests when transcribe module is updated
    # def test_transcribe_module(self):
    #     resp = self.bus.wait_for_response(Message("get_transcripts"))
    #     self.assertIsInstance(resp, Message)
    #     matches = resp.data.get("transcripts")
    #     self.assertIsInstance(matches, list)

    # def test_client_module(self):
    #     resp = self.bus.wait_for_response(Message("neon.client.update_brands"), "neon.server.update_brands.response")
    #     self.assertIsInstance(resp, Message)
    #     data = resp.data
    #     self.assertIsInstance(data["success"], bool)

    def test_skills_module(self):
        response = self.bus.wait_for_response(Message('mycroft.skills.is_ready'))
        self.assertTrue(response.data['status'])

        response = self.bus.wait_for_response(Message("skillmanager.list"), "mycroft.skills.list")
        self.assertIsInstance(response, Message)
        loaded_skills = response.data
        self.assertIsInstance(loaded_skills, dict)
        self.assertGreater(len(loaded_skills.keys()), 1)

    # TODO: Test user utterance -> response


if __name__ == '__main__':
    unittest.main()
