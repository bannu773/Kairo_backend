from flask_restx import Namespace, Resource

api = Namespace('health', description='Health check operations')


@api.route('/health')
class HealthCheck(Resource):
    @api.doc('health_check')
    @api.response(200, 'Service is healthy')
    def get(self):
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'service': 'task-manager-api',
            'version': '1.0.0'
        }, 200


@api.route('/ping')
class Ping(Resource):
    @api.doc('ping')
    @api.response(200, 'Pong')
    def get(self):
        """Simple ping endpoint"""
        return {'message': 'pong'}, 200
