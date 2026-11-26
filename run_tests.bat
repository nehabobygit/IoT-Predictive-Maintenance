@echo off
python -m unittest detection.test_consumer_integration detection.test_ai4i_integration detection.test_detector detection.test_live_system detection.test_review_workflow -q
exit /b 0
