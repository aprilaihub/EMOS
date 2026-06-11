# create_demo.sh
#!/bin/bash
cd /home/soe/EMOS

# Start backend in background
echo "Starting EMOS backend..."
python backend/app.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "Starting EMOS frontend..."
echo "Demo available at: http://localhost:8080"
python3 -m http.server 8080

# Cleanup on exit
trap "kill $BACKEND_PID" EXIT