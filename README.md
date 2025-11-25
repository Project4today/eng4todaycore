# API Documentation: AI Chatbox v1.3

This document provides the necessary API details for the frontend team to implement the chat, chat history, and persona management features, now including voice selection.

## High-Level Overview

The API is divided into three main parts:
1.  **Voices**: Get a list of available text-to-speech voices.
2.  **Persona Management**: A full CRUD API to create, read, update, and delete AI personas, including assigning them a specific voice.
3.  **Chat Interaction**: API endpoints to start chat sessions with a persona and handle messaging.

---

## 1. Voices API (`/api/voices`)

### GET `/api/voices`
-   **Purpose**: Retrieves a list of all available English neural voices from Amazon Polly. Use this to populate voice selection dropdowns in the UI.
-   **Success Response (200 OK)**: An array of `Voice` objects, sorted by language and name.
-   **Example Response**:
    ```json
    [
      {
        "id": "Brian",
        "name": "Brian",
        "gender": "Male",
        "language_code": "en-GB",
        "language_name": "British English"
      },
      {
        "id": "Joanna",
        "name": "Joanna",
        "gender": "Female",
        "language_code": "en-US",
        "language_name": "US English"
      }
    ]
    ```

---

## 2. Persona Management API (`/api/personas`)

These endpoints allow for the management of the AI personalities.

### POST `/api/personas`
-   **Purpose**: Creates a new persona. You can optionally assign a voice upon creation.
-   **Request Body**: A `Persona` object.
    -   `voice_id` (string, optional): The `id` of the voice selected from the `GET /api/voices` endpoint.
-   **Example `curl`**:
    ```sh
    curl -X POST "http://localhost:8000/api/personas" \
         -H "Content-Type: application/json" \
         -d '{
               "role_name": "British Butler",
               "voice_id": "Brian",
               "goal": "To assist with utmost politeness.",
               "personality": "Formal and discreet.",
               "setting": "A formal household."
             }'
    ```

### PUT `/api/personas/{prompt_id}`
-   **Purpose**: Updates an existing persona. This endpoint can be used to change any field, including just the `voice_id`.
-   **Request Body**: A partial `Persona` object. Only include the fields you want to change.
-   **Example `curl` (to change only the voice)**:
    ```sh
    curl -X PUT "http://localhost:8000/api/personas/1" \
         -H "Content-Type: application/json" \
         -d '{ "voice_id": "Matthew" }'
    ```

*(Other Persona endpoints like `GET` and `DELETE` remain the same.)*

---

## 3. Chat Interaction API (`/api/chat`)

These endpoints manage the lifecycle of a user's conversation. The backend now automatically uses the `voice_id` from the session's persona to generate audio.

### POST `/api/chat/start`
-   **Purpose**: Creates a new chat session. The `persona_id` provided will determine the AI's personality and default voice.
-   **Request Body**:
    ```json
    {
      "user_id": 123,
      "persona_id": 1
    }
    ```

### POST `/api/chat/{session_id}/message`
-   **Purpose**: Sends a message and gets a response. Can also be used to change the session's default persona mid-conversation.
-   **Request Body**:
    ```json
    {
      "message": "Please switch to the butler persona now.",
      "persona_id": 5
    }
    ```
    - `persona_id` (integer, optional): If provided, **changes the default persona** for this session for all future messages.

*(Other Chat endpoints remain the same. The `audio_url` in the response is now a temporary, pre-signed URL.)*
