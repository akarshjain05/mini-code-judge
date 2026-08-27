import subprocess
def dangerous_function(user_input):
    subprocess.call(user_input, shell=True)
