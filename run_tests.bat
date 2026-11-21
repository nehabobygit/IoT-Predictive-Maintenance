@echo off
python -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector -q
exit /b 0
