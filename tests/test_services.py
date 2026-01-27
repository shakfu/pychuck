"""Tests for the services layer."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAudioService:
    """Tests for AudioService."""

    def test_init(self):
        """Test AudioService initialization."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)

        assert service.chuck is mock_chuck
        assert service.is_running is False

    def test_init_with_logger(self):
        """Test AudioService with custom logger."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        service = AudioService(mock_chuck, logger=mock_logger)

        assert service._logger is mock_logger

    def test_init_with_custom_timeout(self):
        """Test AudioService with custom shutdown timeout."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck, shutdown_timeout_ms=1000)

        assert service._shutdown_timeout_ms == 1000

    @patch("numchuck.services.audio.start_audio")
    def test_start_success(self, mock_start):
        """Test successful audio start."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)

        assert service.start() is True
        assert service.is_running is True
        mock_start.assert_called_once_with(mock_chuck)

    @patch("numchuck.services.audio.start_audio")
    def test_start_already_running(self, mock_start):
        """Test start when already running."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        assert service.start() is True
        mock_start.assert_not_called()

    @patch("numchuck.services.audio.start_audio")
    def test_start_failure(self, mock_start):
        """Test start failure."""
        from numchuck.services import AudioService

        mock_start.side_effect = RuntimeError("Audio error")
        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)

        assert service.start() is False
        assert service.is_running is False

    @patch("numchuck.services.audio.start_audio")
    def test_start_with_callbacks(self, mock_start):
        """Test start triggers on_start callback."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        mock_callback = MagicMock()
        service = AudioService(mock_chuck)
        service.set_callbacks(on_start=mock_callback)

        result = service.start()

        assert result is True
        assert mock_callback.call_count == 1

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_success(self, mock_shutdown, mock_stop):
        """Test successful audio stop."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        assert service.stop() is True
        assert service.is_running is False

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_not_running(self, mock_shutdown, mock_stop):
        """Test stop when not running."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)

        assert service.stop() is True
        mock_stop.assert_not_called()

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_with_callback(self, mock_shutdown, mock_stop):
        """Test stop triggers on_stop callback."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        mock_callback = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True
        service.set_callbacks(on_stop=mock_callback)

        result = service.stop()

        assert result is True
        assert mock_callback.call_count == 1

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_error_in_stop_audio(self, mock_shutdown, mock_stop):
        """Test stop handles error in stop_audio."""
        from numchuck.services import AudioService

        mock_stop.side_effect = RuntimeError("Stop error")
        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        assert service.stop() is False
        assert service.is_running is False

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_error_in_shutdown(self, mock_shutdown, mock_stop):
        """Test stop handles error in shutdown_audio."""
        from numchuck.services import AudioService

        mock_shutdown.side_effect = RuntimeError("Shutdown error")
        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        assert service.stop() is False

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_shutdown(self, mock_shutdown, mock_stop):
        """Test shutdown method."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        assert service.shutdown() is True
        mock_stop.assert_called_once()
        mock_shutdown.assert_called_once()

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_shutdown_custom_timeout(self, mock_shutdown, mock_stop):
        """Test shutdown with custom timeout."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        result = service.shutdown(timeout_ms=2000)

        assert result is True
        assert mock_shutdown.call_count == 1
        assert mock_shutdown.call_args[0][0] == 2000

    @patch("numchuck.services.audio.start_audio")
    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_restart(self, mock_shutdown, mock_stop, mock_start):
        """Test restart method."""
        from numchuck.services import AudioService

        mock_chuck = MagicMock()
        service = AudioService(mock_chuck)
        service._running = True

        assert service.restart() is True
        mock_stop.assert_called()
        mock_start.assert_called()


class TestShredService:
    """Tests for ShredService."""

    def test_init(self):
        """Test ShredService initialization."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        service = ShredService(mock_chuck)

        assert service.chuck is mock_chuck
        assert service.session is None

    def test_init_with_session(self):
        """Test ShredService with session."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_session = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        assert service.session is mock_session

    def test_spork_code_success(self):
        """Test successful code sporking."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.compile_code.return_value = (True, [1])
        service = ShredService(mock_chuck)

        result = service.spork_code("SinOsc s => dac;")

        assert result.success is True
        assert result.shred_ids == [1]
        assert result.shred_id == 1

    def test_spork_code_failure(self):
        """Test failed code sporking."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.compile_code.return_value = (False, [])
        service = ShredService(mock_chuck)

        result = service.spork_code("invalid code")

        assert result.success is False
        assert result.shred_ids == []

    def test_spork_code_exception(self):
        """Test code sporking handles exception."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.compile_code.side_effect = RuntimeError("Compile error")
        service = ShredService(mock_chuck)

        result = service.spork_code("bad code")

        assert result.success is False
        assert "Compile error" in result.error

    def test_spork_code_with_session(self):
        """Test code sporking updates session."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.compile_code.return_value = (True, [42])
        mock_session = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        result = service.spork_code("SinOsc s => dac;")

        assert result.success is True
        mock_session.add_shred.assert_called()

    def test_spork_code_with_custom_name(self):
        """Test code sporking with custom name."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.compile_code.return_value = (True, [1])
        mock_session = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        service.spork_code("SinOsc s => dac;", name="my_shred")

        mock_session.add_shred.assert_called_once()
        call_args = mock_session.add_shred.call_args
        assert call_args[0][1] == "my_shred"

    def test_spork_file_success(self, tmp_path):
        """Test successful file sporking."""
        from numchuck.services import ShredService

        # Create test file
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        service = ShredService(mock_chuck)

        result = service.spork_file(str(ck_file))

        assert result.success is True
        assert result.shred_ids == [1]

    def test_spork_file_failure(self, tmp_path):
        """Test file sporking failure."""
        from numchuck.services import ShredService

        ck_file = tmp_path / "test.ck"
        ck_file.write_text("invalid")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (False, [])
        service = ShredService(mock_chuck)

        result = service.spork_file(str(ck_file))

        assert result.success is False

    def test_spork_file_with_session(self, tmp_path):
        """Test file sporking updates session."""
        from numchuck.services import ShredService

        ck_file = tmp_path / "test.ck"
        ck_file.write_text("SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_session = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        result = service.spork_file(str(ck_file))

        assert result.success is True
        mock_session.add_shred.assert_called()

    def test_replace_shred_success(self):
        """Test successful shred replacement."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.replace_shred.return_value = 2
        service = ShredService(mock_chuck)

        result = service.replace_shred(1, "new code")

        assert result.success is True
        assert result.shred_ids == [2]

    def test_replace_shred_failure(self):
        """Test shred replacement failure."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.replace_shred.return_value = 0
        service = ShredService(mock_chuck)

        result = service.replace_shred(1, "new code")

        assert result.success is False

    def test_replace_shred_with_session(self):
        """Test shred replacement updates session."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.replace_shred.return_value = 2
        mock_session = MagicMock()
        mock_session.project = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        result = service.replace_shred(1, "new code")

        assert result.success is True
        mock_session.remove_shred.assert_called_with(1)
        mock_session.add_shred.assert_called()
        mock_session.replace_shred.assert_called()

    def test_replace_shred_file_success(self, tmp_path):
        """Test successful file-based shred replacement."""
        from numchuck.services import ShredService

        ck_file = tmp_path / "new.ck"
        ck_file.write_text("new code")

        mock_chuck = MagicMock()
        mock_chuck.replace_shred.return_value = 2
        service = ShredService(mock_chuck)

        result = service.replace_shred_file(1, str(ck_file))

        assert result.success is True
        assert result.shred_ids == [2]

    def test_remove_shred_success(self):
        """Test successful shred removal."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        service = ShredService(mock_chuck)

        assert service.remove_shred(1) is True
        mock_chuck.remove_shred.assert_called_once_with(1)

    def test_remove_shred_failure(self):
        """Test shred removal failure."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.remove_shred.side_effect = RuntimeError("No such shred")
        service = ShredService(mock_chuck)

        assert service.remove_shred(999) is False

    def test_remove_shred_with_session(self):
        """Test shred removal updates session."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_session = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        result = service.remove_shred(1)

        assert result is True
        assert mock_session.remove_shred.call_count == 1
        assert mock_session.remove_shred.call_args[0][0] == 1

    def test_remove_all(self):
        """Test remove all shreds."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        service = ShredService(mock_chuck)

        assert service.remove_all() is True
        mock_chuck.remove_all_shreds.assert_called_once()

    def test_remove_all_with_session(self):
        """Test remove all updates session."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_session = MagicMock()
        service = ShredService(mock_chuck, session=mock_session)

        result = service.remove_all()

        assert result is True
        assert mock_session.clear_shreds.call_count >= 1

    def test_clear_vm(self):
        """Test clear VM."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        service = ShredService(mock_chuck)

        assert service.clear_vm() is True
        mock_chuck.clear_vm.assert_called_once()

    def test_reset_shred_id(self):
        """Test reset shred ID."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        service = ShredService(mock_chuck)

        assert service.reset_shred_id() is True
        mock_chuck.reset_shred_id.assert_called_once()

    def test_list_shreds(self):
        """Test list shreds."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.get_all_shred_ids.return_value = [1, 2, 3]
        service = ShredService(mock_chuck)

        result = service.list_shreds()

        assert result == [1, 2, 3]

    def test_list_shreds_error(self):
        """Test list shreds handles error."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.get_all_shred_ids.side_effect = RuntimeError("Error")
        service = ShredService(mock_chuck)

        result = service.list_shreds()

        assert result == []

    def test_get_shred_info(self):
        """Test get shred info."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.get_shred_info.return_value = {
            "id": 1,
            "name": "test",
            "is_running": True,
            "is_done": False,
        }
        service = ShredService(mock_chuck)

        info = service.get_shred_info(1)

        assert info is not None
        assert info.id == 1
        assert info.name == "test"
        assert info.is_running is True

    def test_get_shred_info_not_found(self):
        """Test get shred info for non-existent shred."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.get_shred_info.side_effect = RuntimeError("Not found")
        service = ShredService(mock_chuck)

        info = service.get_shred_info(999)

        assert info is None

    def test_compile_file(self, tmp_path):
        """Test compile file (syntax check)."""
        from numchuck.services import ShredService

        ck_file = tmp_path / "test.ck"
        ck_file.write_text("SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [])
        service = ShredService(mock_chuck)

        assert service.compile_file(str(ck_file)) is True
        mock_chuck.compile_file.assert_called_with(str(ck_file), count=0)

    def test_exec_code(self):
        """Test exec code (immediate)."""
        from numchuck.services import ShredService

        mock_chuck = MagicMock()
        mock_chuck.compile_code.return_value = (True, [])
        service = ShredService(mock_chuck)

        assert service.exec_code("<<< 'hello' >>>;") is True
        mock_chuck.compile_code.assert_called_with("<<< 'hello' >>>;", immediate=True)

    def test_shred_result_properties(self):
        """Test ShredResult dataclass."""
        from numchuck.services import ShredResult

        result = ShredResult(success=True, shred_ids=[1, 2, 3])
        assert result.shred_id == 1

        empty_result = ShredResult(success=False, shred_ids=[])
        assert empty_result.shred_id is None


class TestGlobalsService:
    """Tests for GlobalsService."""

    def test_init(self):
        """Test GlobalsService initialization."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.chuck is mock_chuck

    def test_set_global_int(self):
        """Test setting an integer global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global("myInt", 42) is True
        mock_chuck.set_global_int.assert_called_once_with("myInt", 42)

    def test_set_global_float(self):
        """Test setting a float global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global("myFloat", 3.14) is True
        mock_chuck.set_global_float.assert_called_once_with("myFloat", 3.14)

    def test_set_global_string(self):
        """Test setting a string global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global("myStr", "hello") is True
        mock_chuck.set_global_string.assert_called_once_with("myStr", "hello")

    def test_set_global_int_array(self):
        """Test setting an int array global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global("myArray", [1, 2, 3]) is True
        mock_chuck.set_global_int_array.assert_called_once_with("myArray", [1, 2, 3])

    def test_set_global_float_array(self):
        """Test setting a float array global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global("myArray", [1.0, 2.0, 3.0]) is True
        mock_chuck.set_global_float_array.assert_called_once()

    def test_set_global_mixed_array(self):
        """Test setting a mixed int/float array converts to float."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global("myArray", [1, 2.5, 3]) is True
        mock_chuck.set_global_float_array.assert_called_once()

    def test_set_global_error(self):
        """Test set global handles error."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.set_global_int.side_effect = RuntimeError("Error")
        service = GlobalsService(mock_chuck)

        assert service.set_global("myInt", 42) is False

    def test_set_global_int_direct(self):
        """Test set_global_int directly."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global_int("x", 10) is True
        mock_chuck.set_global_int.assert_called_with("x", 10)

    def test_set_global_float_direct(self):
        """Test set_global_float directly."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global_float("x", 1.5) is True
        mock_chuck.set_global_float.assert_called_with("x", 1.5)

    def test_set_global_string_direct(self):
        """Test set_global_string directly."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global_string("x", "test") is True
        mock_chuck.set_global_string.assert_called_with("x", "test")

    def test_set_global_int_array_direct(self):
        """Test set_global_int_array directly."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global_int_array("x", [1, 2]) is True
        mock_chuck.set_global_int_array.assert_called_with("x", [1, 2])

    def test_set_global_float_array_direct(self):
        """Test set_global_float_array directly."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.set_global_float_array("x", [1.0, 2.0]) is True
        mock_chuck.set_global_float_array.assert_called_with("x", [1.0, 2.0])

    def test_get_global_int(self):
        """Test getting an integer global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()

        def mock_get(name, callback):
            callback(42)

        mock_chuck.get_global_int.side_effect = mock_get
        service = GlobalsService(mock_chuck)

        result = service.get_global_int("myInt")

        assert result == 42

    def test_get_global_int_not_found(self):
        """Test getting non-existent int global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.get_global_int.side_effect = RuntimeError("Not found")
        service = GlobalsService(mock_chuck)

        result = service.get_global_int("missing")

        assert result is None

    def test_get_global_float(self):
        """Test getting a float global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()

        def mock_get(name, callback):
            callback(3.14)

        mock_chuck.get_global_float.side_effect = mock_get
        service = GlobalsService(mock_chuck)

        result = service.get_global_float("myFloat")

        assert result == 3.14

    def test_get_global_string(self):
        """Test getting a string global."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()

        def mock_get(name, callback):
            callback("hello")

        mock_chuck.get_global_string.side_effect = mock_get
        service = GlobalsService(mock_chuck)

        result = service.get_global_string("myStr")

        assert result == "hello"

    def test_get_global_auto_detect_int(self):
        """Test get_global auto-detects int type."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()

        def mock_get_int(name, callback):
            callback(42)

        mock_chuck.get_global_int.side_effect = mock_get_int
        service = GlobalsService(mock_chuck)

        result = service.get_global("myVar")

        assert result == ("int", 42)

    def test_get_global_auto_detect_float(self):
        """Test get_global auto-detects float type."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.get_global_int.side_effect = RuntimeError("Not int")

        def mock_get_float(name, callback):
            callback(3.14)

        mock_chuck.get_global_float.side_effect = mock_get_float
        service = GlobalsService(mock_chuck)

        result = service.get_global("myVar")

        assert result == ("float", 3.14)

    def test_get_global_auto_detect_string(self):
        """Test get_global auto-detects string type."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.get_global_int.side_effect = RuntimeError("Not int")
        mock_chuck.get_global_float.side_effect = RuntimeError("Not float")

        def mock_get_string(name, callback):
            callback("hello")

        mock_chuck.get_global_string.side_effect = mock_get_string
        service = GlobalsService(mock_chuck)

        result = service.get_global("myVar")

        assert result == ("string", "hello")

    def test_get_global_not_found(self):
        """Test get_global returns None when not found."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.get_global_int.side_effect = RuntimeError("Not found")
        mock_chuck.get_global_float.side_effect = RuntimeError("Not found")
        mock_chuck.get_global_string.side_effect = RuntimeError("Not found")
        service = GlobalsService(mock_chuck)

        result = service.get_global("missing")

        assert result is None

    def test_list_globals(self):
        """Test listing globals."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.get_all_globals.return_value = [("int", "x"), ("float", "y")]
        service = GlobalsService(mock_chuck)

        result = service.list_globals()

        assert len(result) == 2
        assert result[0].name == "x"
        assert result[0].type == "int"

    def test_list_globals_error(self):
        """Test list globals handles error."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.get_all_globals.side_effect = RuntimeError("Error")
        service = GlobalsService(mock_chuck)

        result = service.list_globals()

        assert result == []

    def test_signal_event(self):
        """Test signaling an event."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.signal_event("myEvent") is True
        mock_chuck.signal_global_event.assert_called_once_with("myEvent")

    def test_signal_event_error(self):
        """Test signal event handles error."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.signal_global_event.side_effect = RuntimeError("Error")
        service = GlobalsService(mock_chuck)

        assert service.signal_event("myEvent") is False

    def test_broadcast_event(self):
        """Test broadcasting an event."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        service = GlobalsService(mock_chuck)

        assert service.broadcast_event("myEvent") is True
        mock_chuck.broadcast_global_event.assert_called_once_with("myEvent")

    def test_broadcast_event_error(self):
        """Test broadcast event handles error."""
        from numchuck.services import GlobalsService

        mock_chuck = MagicMock()
        mock_chuck.broadcast_global_event.side_effect = RuntimeError("Error")
        service = GlobalsService(mock_chuck)

        assert service.broadcast_event("myEvent") is False


class TestFileService:
    """Tests for FileService."""

    def test_init(self):
        """Test FileService initialization."""
        from numchuck.services import FileService

        service = FileService()
        assert service.session is None

    def test_init_with_session(self):
        """Test FileService with session."""
        from numchuck.services import FileService

        mock_session = MagicMock()
        service = FileService(session=mock_session)
        assert service.session is mock_session

    def test_load_snippet_not_found(self):
        """Test loading non-existent snippet."""
        from numchuck.services import FileService

        service = FileService()
        result = service.load_snippet("nonexistent_snippet_xyz")
        assert result is None

    @patch("numchuck.services.files.get_snippet_path_with_source")
    def test_load_snippet_success(self, mock_get_snippet, tmp_path):
        """Test loading existing snippet."""
        from numchuck.services import FileService

        snippet_file = tmp_path / "test.ck"
        snippet_file.write_text("SinOsc s => dac;")
        mock_get_snippet.return_value = (snippet_file, "local")

        service = FileService()
        result = service.load_snippet("test")

        assert result is not None
        assert result.name == "test"
        assert result.path == snippet_file
        assert result.source == "local"
        assert "SinOsc" in result.content

    @patch("numchuck.services.files.list_all_snippets")
    @patch("numchuck.services.files.get_snippet_path_with_source")
    def test_list_snippets(self, mock_get_snippet, mock_list, tmp_path):
        """Test listing snippets."""
        from numchuck.services import FileService

        snippet_file = tmp_path / "sine.ck"
        snippet_file.write_text("SinOsc s => dac;")
        mock_list.return_value = [("sine", "local"), ("noise", "global")]
        mock_get_snippet.return_value = (snippet_file, "local")

        service = FileService()
        result = service.list_snippets()

        assert len(result) == 2

    def test_get_snippets_dir(self):
        """Test getting snippets directory."""
        from numchuck.services import FileService

        service = FileService()
        snippets_dir = service.get_snippets_dir()
        assert snippets_dir is not None

    def test_ensure_directories(self):
        """Test ensuring directories exist."""
        from numchuck.services import FileService

        service = FileService()
        # Should not raise
        result = service.ensure_directories()
        assert result is True

    def test_save_to_project_no_session(self):
        """Test save to project without session."""
        from numchuck.services import FileService

        service = FileService()
        result = service.save_to_project("test", "content", 1)
        assert result is False

    def test_save_to_project_no_project(self):
        """Test save to project without project."""
        from numchuck.services import FileService

        mock_session = MagicMock()
        mock_session.project = None
        service = FileService(session=mock_session)

        result = service.save_to_project("test", "content", 1)
        assert result is False

    def test_save_to_project_success(self):
        """Test save to project success."""
        from numchuck.services import FileService

        mock_session = MagicMock()
        mock_session.project = MagicMock()
        service = FileService(session=mock_session)

        result = service.save_to_project("test", "content", 1)

        assert result is True
        mock_session.project.save_on_spork.assert_called_once_with("test", "content", 1)

    def test_save_replacement_to_project_success(self):
        """Test save replacement to project."""
        from numchuck.services import FileService

        mock_session = MagicMock()
        mock_session.project = MagicMock()
        service = FileService(session=mock_session)

        result = service.save_replacement_to_project(1, "new content")

        assert result is True
        mock_session.project.save_on_replace.assert_called_once_with(1, "new content")

    def test_read_file_success(self, tmp_path):
        """Test reading existing file."""
        from numchuck.services import FileService

        test_file = tmp_path / "test.ck"
        test_file.write_text("SinOsc s => dac;")

        service = FileService()
        result = service.read_file(str(test_file))

        assert result == "SinOsc s => dac;"

    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        from numchuck.services import FileService

        service = FileService()
        result = service.read_file("/nonexistent/path/file.ck")
        assert result is None

    def test_read_file_with_path_object(self, tmp_path):
        """Test reading file with Path object."""
        from numchuck.services import FileService

        test_file = tmp_path / "test.ck"
        test_file.write_text("test content")

        service = FileService()
        result = service.read_file(test_file)

        assert result == "test content"


class TestWidgets:
    """Tests for widget factory functions."""

    def test_create_help_window(self):
        """Test creating help window."""
        from numchuck.tui.widgets import create_help_window
        from prompt_toolkit.layout.containers import ConditionalContainer

        def show() -> bool:
            return True

        window = create_help_window(show, "Help text")
        assert isinstance(window, ConditionalContainer)

    def test_create_shreds_table(self):
        """Test creating shreds table."""
        from numchuck.tui.widgets import create_shreds_table
        from prompt_toolkit.layout.containers import ConditionalContainer

        def show() -> bool:
            return True

        def get_text() -> str:
            return "No shreds"

        table = create_shreds_table(show, get_text)
        assert isinstance(table, ConditionalContainer)

    def test_create_log_window(self):
        """Test creating log window."""
        from numchuck.tui.widgets import create_log_window
        from prompt_toolkit.layout.containers import ConditionalContainer
        from prompt_toolkit.widgets import TextArea

        def show() -> bool:
            return True

        container, log_area = create_log_window(show)
        assert isinstance(container, ConditionalContainer)
        assert isinstance(log_area, TextArea)

    def test_create_status_bar(self):
        """Test creating status bar."""
        from numchuck.tui.widgets import create_status_bar
        from prompt_toolkit.layout.containers import Window

        def get_status() -> str:
            return "Status"

        bar = create_status_bar(get_status)
        assert isinstance(bar, Window)

    def test_create_message_area(self):
        """Test creating message area."""
        from numchuck.tui.widgets import create_message_area
        from prompt_toolkit.widgets import TextArea

        area = create_message_area("Initial text")
        assert isinstance(area, TextArea)
