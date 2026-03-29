ChessOnline: Real-Time Cloud-Synced Application

A full-stack chess application featuring a **distributed system architecture**. This project demonstrates the orchestration of a **Python-based backend** with a custom **JavaScript/HTML5 frontend**, synchronized globally via a **Firebase NoSQL** database.

System Architecture

Unlike a local script, this application operates as a live web service where the game state is managed in the cloud:

* Backend Orchestrator (Python & Streamlit):** Manages server-side environment configurations, handles secure API handshakes via Streamlit Secrets, and serves the core web application.
* Real-Time Data Layer (Firebase Firestore):** Utilizes a **NoSQL Document Store** to persist game states (FEN strings) and clock synchronization, enabling sub-2-second latency between moves across global clients.
* Hybrid Frontend:** A custom-engineered interface using **JavaScript** for move logic and **CSS3** for dynamic, state-based animations (such as the pulsing low-time indicator).

Tech Stack

* Language:** Python 3.x
* Cloud Database:** Google Firebase Firestore
* Framework:** Streamlit
* Frontend Logic:** JavaScript (Chess.js integration)
* Styling:** Custom CSS3 (Dark Mode Optimized)

Engineering Features

* Cross-Client Synchronization:** Moves played on one device are instantly reflected for the opponent via asynchronous REST API polling.
* State Persistence:** Game state is retrieved automatically from Firebase upon browser refresh, ensuring zero data loss during sessions.
* Security Integration:** Implements secure credential management using encrypted environment variables to protect sensitive service account data.
* Modular Web Components:** Seamlessly blends Python backend logic with custom HTML/JS components for a high-performance user experience.

Local Execution

1.  Clone the Repository:**
    ```zsh
    git clone [https://github.com/henrykang10/chess-online.git](https://github.com/henrykang10/chess-online.git)
    cd chess-online
    ```

2.  Install Dependencies:**
    ```zsh
    pip install -r requirements.txt
    ```

3.  Environment Setup:**
    Ensure your `firebase_key.json` is present in the root directory or configured via `st.secrets`.

4.  Launch the App:**
    ```zsh
    streamlit run app.py
    ```
