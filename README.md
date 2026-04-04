LogLens:
    Requirements.txt: 
        This is a txt file that includes all the requiremnets (Extensions and System requirements) for error free execution of the loglens program.

        Open Terminal and run the command:
        pip install -r requirements.txt

        This will automatically install all the requiremnets in your device.



    Logs:
        Sample.log: Includes a sample of logs for test run and to stimulate how the program will execute in real life situation.
    
    loglens:
        parser.py:
            Parser is the primary file that executes initially. The parser.py is responsible for making sure that the logs are parsed into the dictionary one at a time and to return none if the line does not match the expected format using RegEx.


