import subprocess

# List of Python files to run
python_files = ['/Users/mouaidnasab/Documents/personal projects/Finance App V.2/init_db/init_db.py', '/Users/mouaidnasab/Documents/personal projects/Finance App V.2/init_db/insert members.py', '/Users/mouaidnasab/Documents/personal projects/Finance App V.2/init_db/insert Accounts.py', '/Users/mouaidnasab/Documents/personal projects/Finance App V.2/init_db/insert transactions.py']

# Loop through the list and run each file
for file in python_files:
    try:
        # Run the Python file
        result = subprocess.run(['/opt/homebrew/bin/python3.11', file], check=True, capture_output=True, text=True)
        # Print the output of the Python file
        print(f"Output of {file}:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        # Print the error if the Python file fails to run
        print(f"Error occurred while running {file}:")
        print(e.stderr)
