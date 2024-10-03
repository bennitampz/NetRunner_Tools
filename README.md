# NetRunner--Vulnerability-Scanner-Tool

NetRunner is a vulnerability scanning tool written in Python. This tool is designed to assist security testers in identifying various types of vulnerabilities on websites, including but not limited to XSS, SQL Injection, Local File Inclusion (LFI), Remote File Inclusion (RFI), and more.

Key Features
  - URL Crawling: Fetches and collects links from web pages for further analysis.
  - Vulnerability Testing: Provides tests for various common vulnerabilities in web applications.
  - Formatted Reports: Generates reports in HTML format that are easy to read for further analysis.
Prerequisites
    Before running NetRunner, ensure you have the following prerequisites:

Python 3: Make sure Python 3.x is installed on your system. You can check your Python version by running:
Required Libraries: You need to install two Python libraries:
    
- requests: Used for sending HTTP requests.

- beautifulsoup4: Used for parsing HTML and XML.

Use : python3 --version

      git clone https://github.com/bennitampz/NetRunner--Vulnerability-Scanner-Tool
	  
      cd NetRunner--Vulnerability-Scanner-Tool
	  
      pip install requests beautifulsoup4
	  
Prepare Input File:

    Create a text file containing the list of URLs you want to scan. Each URL should be on a separate line. Example format for the file (urls.txt):
	
    Inside .txt like
	
    - http://example.com
	
    - http://testsite.com
	
 After preparing the input file, run NetRunner with the following command:
 
    python3 NetRunner.py urls.txt
	
Scan Results:

The scan results will be saved in an HTML file generated based on the input file name, ending with _results.html. For example, if the input file is urls.txt,

the results will be saved as urls_results.html.
