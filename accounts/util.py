
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
import datetime
import jwt
from accounts.models import User
def get_tokens_for_user(user):
    refresh_token = RefreshToken.for_user(user)
    access_token = AccessToken.for_user(user)
    payload = {
                "id": user.id,
                "email": user.email,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
                "iat": datetime.datetime.utcnow()
            }

    jwt_token = jwt.encode(payload, 'secret', algorithm='HS256')
    return {
        'refresh_token': str(refresh_token),
        'access_token': str(access_token),
        'jwt_token': str(jwt_token)
    }
def get_user(request):
    user = User.objects.filter(request.user)
    if user:
        return user
    return False