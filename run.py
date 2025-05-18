from app import create_app, db, socketio
import os

app = create_app()

if __name__ == '__main__':
    # Ensure the database is created
    with app.app_context():
        db.create_all()

    # Check for face-api.js model files
    face_models_dir = os.path.join(app.static_folder, 'face-api-models')
    if not os.path.exists(face_models_dir) or not os.listdir(face_models_dir):
        print("  Face detection models not found.")
        print(" Download models from:")
        print("   https://github.com/justadudewhohacks/face-api.js/tree/master/weights")
        print(f"   And place them in: {face_models_dir}\n")

    # Run with Flask-SocketIO for real-time messaging
    socketio.run(app, debug=True)

    # For production with SSL, uncomment and configure:
    # socketio.run(
    #     app,
    #     host='0.0.0.0',
    #     port=443,
    #     debug=False,
    #     ssl_context=(app.config['SSL_CERT'], app.config['SSL_KEY'])
    # )
