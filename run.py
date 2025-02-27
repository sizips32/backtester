import streamlit.web.cli as stcli
import sys

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "app.py", 
                "--server.port=7700", 
                "--server.headless=true"]
    sys.exit(stcli.main()) 
