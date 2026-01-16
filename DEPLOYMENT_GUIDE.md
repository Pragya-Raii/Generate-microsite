# 🚀 All-in-One Deployment on Render

Deploy both your Frontend and Backend to **Render** using a single configuration file. This is the easiest way to manage your full-stack application.

## Prerequisites
1.  A [Render Account](https://render.com/).
2.  Your code pushed to a **GitHub Repository**.

## Steps to Deploy

1.  **Go to Render Dashboard**:
    *   Click **New +** -> **Blueprint**.

2.  **Connect your Repository**:
    *   Select your `WebAgent` repository.

3.  **Configure the Blueprint**:
    *   Render will automatically detect the `render.yaml` file in the root directory.
    *   It will show two services to be created:
        *   `webagent-backend` (Python Web Service)
        *   `webagent-frontend` (Static Site)

4.  **Set Environment Variables**:
    *   You will be prompted to enter values for:
        *   `NVIDIA_API_KEY`: Paste your NVIDIA API key here.
        *   `OPENROUTER_API_KEY`: Paste your OpenRouter API key here.
    *   *Note: `VITE_BACKEND_URL` is automatically wired up by the Blueprint!*

5.  **Click Apply**:
    *   Render will start deploying both services.
    *   The **Backend** will build first (installing Python deps).
    *   The **Frontend** will build next (building React).

## Access Your App
Once deployment is complete:
1.  Find the `webagent-frontend` service in your dashboard.
2.  Click the URL (e.g., `https://webagent-frontend.onrender.com`).
3.  Your AI Website Builder is now live! 🚀

## Troubleshooting
*   **Backend Logs**: If generation fails, check the logs of the `webagent-backend` service.
*   **Build Failures**: Ensure your `requirements.txt` and `package.json` are in the correct folders (`backend/` and `frontend/`).
