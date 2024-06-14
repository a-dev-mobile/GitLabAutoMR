import sys

def add_certificate(cert_content, script_file='scripts/main.py'):
    with open(script_file, 'r') as file:
        lines = file.readlines()
    
    lines[10] = f'CERTIFICATE = """{cert_content}"""\n'
    
    with open(script_file, 'w') as file:
        file.writelines(lines)

if __name__ == "__main__":
    cert_content = sys.argv[1]
    add_certificate(cert_content)
