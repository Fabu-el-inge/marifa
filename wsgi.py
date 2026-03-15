import logging
from app import create_app

app = create_app('production')

# Log errors to stdout so Render captures them
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    app.logger.error(f'Unhandled exception: {traceback.format_exc()}')
    return 'Internal Server Error', 500
