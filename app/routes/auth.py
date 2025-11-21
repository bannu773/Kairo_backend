from flask import request, redirect, jsonify, current_app
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

from app.models.user import User

api = Namespace('auth', description='Authentication operations')

# Models for Swagger documentation
user_model = api.model('User', {
    'id': fields.String(description='User ID'),
    'email': fields.String(description='User email'),
    'name': fields.String(description='User name'),
    'picture': fields.String(description='Profile picture URL'),
    'role': fields.String(description='User role'),
})

auth_response = api.model('AuthResponse', {
    'success': fields.Boolean(description='Success status'),
    'data': fields.Nested(api.model('AuthData', {
        'token': fields.String(description='JWT access token'),
        'user': fields.Nested(user_model)
    }))
})


@api.route('/login')
class Login(Resource):
    @api.doc('google_login')
    @api.response(302, 'Redirect to Google OAuth')
    def get(self):
        """Initiate Google OAuth login flow"""
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']]
                }
            },
            scopes=current_app.config['ALL_GOOGLE_SCOPES']  # Updated to include Calendar and Drive
        )
        
        flow.redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return redirect(authorization_url)


@api.route('/callback')
class Callback(Resource):
    @api.doc('google_callback')
    @api.response(200, 'Success', auth_response)
    def get(self):
        """Handle Google OAuth callback"""
        try:
            # Get authorization code from query parameters
            code = request.args.get('code')
            
            if not code:
                return {'success': False, 'error': 'No authorization code provided'}, 400
            
            # Exchange authorization code for tokens
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                        "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']]
                    }
                },
                scopes=current_app.config['ALL_GOOGLE_SCOPES']  # Updated to include Calendar and Drive
            )
            
            flow.redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            # Get user info from Google
            from googleapiclient.discovery import build
            user_info_service = build('oauth2', 'v2', credentials=credentials)
            user_info = user_info_service.userinfo().get().execute()
            
            # Check if user exists
            user = User.find_by_google_id(user_info['id'])
            
            if not user:
                # Create new user
                user = User.create(
                    email=user_info['email'],
                    name=user_info.get('name', ''),
                    picture=user_info.get('picture', ''),
                    google_id=user_info['id']
                )
            
            # Update refresh token and all OAuth tokens
            if credentials.refresh_token:
                User.update_refresh_token(str(user['_id']), credentials.refresh_token)
            
            # Store tokens for all Google services (Calendar and Drive use the same OAuth credentials)
            tokens = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            # Update Calendar and Drive tokens with the same credentials
            User.update_calendar_tokens(str(user['_id']), tokens)
            User.update_drive_tokens(str(user['_id']), tokens)
            
            # Create JWT token
            access_token = create_access_token(identity=str(user['_id']))
            
            # Redirect to frontend with token
            frontend_url = current_app.config['FRONTEND_URL']
            redirect_url = f"{frontend_url}/auth/callback?token={access_token}"
            
            return redirect(redirect_url)
            
        except Exception as e:
            print(f"OAuth callback error: {e}")
            return {'success': False, 'error': str(e)}, 500


@api.route('/me')
class CurrentUser(Resource):
    @api.doc('get_current_user', security='Bearer')
    @api.response(200, 'Success', user_model)
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get current authenticated user"""
        try:
            user_id = get_jwt_identity()
            user = User.find_by_id(user_id)
            
            if not user:
                return {'success': False, 'error': 'User not found'}, 404
            
            return {
                'success': True,
                'data': User.serialize(user)
            }, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@api.route('/logout')
class Logout(Resource):
    @api.doc('logout', security='Bearer')
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Logout current user"""
        # With JWT, logout is handled on the client side by removing the token
        # Server-side logout would require token blacklisting (optional feature)
        return {
            'success': True,
            'message': 'Logged out successfully'
        }, 200
