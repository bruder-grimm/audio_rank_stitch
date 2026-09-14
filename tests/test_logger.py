from util.logger import LogLevel, Logger


def test_logger_levels_and_message_format(capsys):
    logger = Logger(level=LogLevel.DEBUG)
    logger.debug("debug message")
    logger.info("info message")
    logger.warn("warn message")
    logger.error("error message")

    captured = capsys.readouterr()
    assert "[DEBUG] debug message" in captured.out
    assert "[INFO] info message" in captured.out
    assert "[WARNING] warn message" in captured.out
    assert "[ERROR]" in captured.out


def test_logger_respects_level(capsys):
    logger = Logger(level=LogLevel.WARNING)
    logger.debug("hidden")
    logger.info("hidden")
    logger.warn("shown")
    logger.error("shown")

    captured = capsys.readouterr()
    assert "hidden" not in captured.out
    assert "shown" in captured.out
