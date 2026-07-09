import os, glob

for filepath in glob.glob('/Users/a91732/Downloads/files/frontend/js/**/*.js', recursive=True):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 1. Remove Authorization headers
    content = content.replace(", 'Authorization': `Bearer ${token}`", "")
    content = content.replace("'Authorization': `Bearer ${token}`, ", "")
    content = content.replace(", 'Authorization':`Bearer ${token}`", "")
    content = content.replace("'Authorization':`Bearer ${token}`, ", "")
    content = content.replace("{ 'Authorization': `Bearer ${token}` }", "{}")
    content = content.replace("{'Authorization': `Bearer ${token}`}", "{}")
    content = content.replace("{'Authorization':`Bearer ${token}`}", "{}")
    content = content.replace("{ 'Authorization':`Bearer ${token}` }", "{}")
    content = content.replace("{ 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }", "{ 'Content-Type': 'application/json' }")
    content = content.replace("{ 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }", "{ 'Content-Type': 'application/json' }")
    
    # 2. Update config.js specifically
    if filepath.endswith('config.js'):
        content = content.replace(
            "let token    = localStorage.getItem('jwt') || null;",
            "let token    = localStorage.getItem('username') ? 'cookie_auth' : null;\n\n"
            "const originalFetch = window.fetch;\n"
            "window.fetch = async function(url, options = {}) {\n"
            "  options.credentials = 'include';\n"
            "  if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase())) {\n"
            "    options.headers = options.headers || {};\n"
            "    options.headers['X-Requested-With'] = 'XMLHttpRequest';\n"
            "  }\n"
            "  return originalFetch(url, options);\n"
            "};\n"
        )
    
    # 3. Update finishLogin in auth.js & router.js
    content = content.replace("async function finishLogin(accessToken) {", "async function finishLogin() {")
    content = content.replace("token = accessToken;", "token = 'cookie_auth';")
    content = content.replace("localStorage.setItem('jwt', token);", "")
    content = content.replace("await finishLogin(data.access_token);", "await finishLogin();")
    content = content.replace("await finishLogin(loginData.access_token);", "await finishLogin();")
    
    # 4. Remove other jwt localStorage stuff
    content = content.replace("localStorage.removeItem('jwt');", "")

    with open(filepath, 'w') as f:
        f.write(content)

print("Frontend fix complete.")
