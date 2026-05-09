import requests

url_login = 'http://localhost:8001/edu/login/'
client = requests.session()

# get CSRF token
client.get(url_login)
csrftoken = client.cookies.get('csrftoken')

if not csrftoken:
    print("Could not get CSRF token")
else:
    data = {
        'username': 'sabari',
        'password': '1234',
        'csrfmiddlewaretoken': csrftoken
    }
    headers = {'Referer': url_login}
    response = client.post(url_login, data=data, headers=headers)
    print("Login status:", response.status_code)
    
    if response.url.endswith('/edu/'):
        print("Redirected to dashboard successfully")
        dash_response = client.get('http://localhost:8001/edu/')
        print("Dashboard Status:", dash_response.status_code)
        if 'Add Identity' in dash_response.text:
            print("SUCCESS: Add Identity button found on dashboard")
        else:
            print("ERROR: Add Identity button NOT found on dashboard")
            # Save the dashboard HTML for inspection
            with open('/tmp/dashboard.html', 'w') as f:
                f.write(dash_response.text)
            print("Dashboard HTML saved to /tmp/dashboard.html for inspection")
    else:
        print("Login failed. Current URL:", response.url)
