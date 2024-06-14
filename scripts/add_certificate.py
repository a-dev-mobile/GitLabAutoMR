import os
import re

def add_certificate(cert_content, script_file='scripts/main.py'):
    with open(script_file, 'r', encoding='utf-8') as file:
        script_content = file.read()
    
    new_content = re.sub(r'CERTIFICATE\s*=\s*""".*?"""', f'CERTIFICATE = """{cert_content}"""', script_content, flags=re.DOTALL)
    
    with open(script_file, 'w', encoding='utf-8') as file:
        file.write(new_content)

if __name__ == "__main__":
    cert_content = os.getenv('CERTIFICATE')
    if cert_content:
        add_certificate(cert_content)
    else:
        print("Certificate content not found in environment variables.")
        exit(1)
