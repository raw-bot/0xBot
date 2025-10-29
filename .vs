{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "🚀 Start Full Stack",
            "type": "shell",
            "command": "./dev.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared",
                "showReuseMessage": true,
                "clear": false
            },
            "problemMatcher": []
        },
        {
            "label": "🐳 Start Docker Services",
            "type": "shell",
            "command": "docker-compose up -d",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "🔧 Backend Setup",
            "type": "shell",
            "command": "cd backend && source venv/bin/activate && ./venv/bin/python -m uvicorn src.main:app --reload",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated"
            },
            "problemMatcher": []
        },
        {
            "label": "⚛️  Frontend Dev",
            "type": "shell",
            "command": "cd frontend && npm run dev",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated"
            },
            "problemMatcher": []
        },
        {
            "label": "🔍 Backend Tests",
            "type": "shell",
            "command": "cd backend && source venv/bin/activate && python -m pytest",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "🧹 Format Code (Backend)",
            "type": "shell",
            "command": "cd backend && source venv/bin/activate && black . && isort .",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "silent",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "🧹 Type Check (Backend)",
            "type": "shell",
            "command": "cd backend && source venv/bin/activate && mypy src",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "📊 View Logs",
            "type": "shell",
            "command": "tail -f backend.log",
            "group": "build",
            "presentation": {
                "echo": false,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated"
            },
            "problemMatcher": []
        },
        {
            "label": "🔄 Reset All",
            "type": "shell",
            "command": "./backend/scripts/reset.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        }
    ]
}
