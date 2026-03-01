import main
for route in main.app.routes:
    print(f"Path: {route.path}, Methods: {route.methods}")
