Project Deliverable 1 Overview

This document provides an overview of the contents included in the first project deliverable.

The first deliverable focuses on setting up the project structure. The main emphasis is on organizing the required files and folders, along with the requirements.txt file, which contains all dependencies needed to run the project on any device supporting VS Code.

Code Content
1. loglen/parser.py

This is the first implemented module and serves as one of the core components of the program. It is responsible for parsing logs and validating their structure.

The parser ensures that logs are correctly formatted and checks them for validity. If a log is valid, it is parsed and divided into key sections such as log level and timestamp. Because of this functionality, it forms a central part of the system.

Additionally, this module supports parsing both entire log files and individual log entries.

2. logs/sample.log

This file contains sample logs commonly found in a typical server environment. While it does not serve a major functional purpose at this stage, it provides an early example of the type of data the program is designed to handle once fully developed.

3. tests/test_parser.py

This file contains tests specifically for parser.py. It verifies both the individual log parsing functionality and the file-based parsing functionality.

The purpose of these tests is to ensure that the parser correctly detects errors and anomalies, and behaves as expected under different scenarios.