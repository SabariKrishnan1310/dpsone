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
        dash_response = client.get('http://localhost:8001/edu/api/dashboard-data/')
        print("Dashboard API Status:", dash_response.status_code)
        print("Dashboard Data:", dash_response.json())

