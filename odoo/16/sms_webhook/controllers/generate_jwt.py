import jwt

SECRET_KEY = 'immersive-helpdesk-2024'

# Payload data
payload = {
    'user_id': 'zohodesk'
}

# Generate JWT token
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
print(token)
#payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
#print(payload)