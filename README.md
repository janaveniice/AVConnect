# AVConnect: Building Trust and Ensuring Safety for Automated Vehicle Users

## Overview
AVConnect is a community-driven platform designed for Automated Vehicle (AV) users to engage with the AV community, manage their AV settings, and foster trust in AV technology. 
The platform empowers users to share experiences, learn from others, and access resources related to AV safety and best practices. By creating a user-friendly interface, AVConnect aims to become the go-to hub for AV enthusiasts, promoting collaboration, education, and confidence in autonomous driving. 
This project was co-deployed by INF2002 2024 Team 28.

## Problem Statement and Purpose
As autonomous vehicles become more prevalent, users often face challenges in understanding and trusting the technology. 
AVConnect addresses this by leveraging Human-Computer Interaction (HCI) principles such as needfinding, task analysis, identifying user needs, prototyping, evaluation, implementation, and experimental design to design an interface that prioritizes user needs, enhances transparency, and ensures safety. 
By fostering a sense of community and providing clear, actionable insights, AVConnect aims to bridge the gap between users and AV technology.

## Features
1. **Update AV metrics**: Users can update their AV settings (e.g. battery, tire pressure). If the metrics fall below standard safety values, it will raise a flag for users to either schedule a maintenance or view related links to troubleshoot the issue. <br>
2. **Create maintenance schedule**: Users can create a maintenance schedule with the necessary details (e.g. title, description, location, date) that serves as a reminder for users.<br>
3. **Discussion Forum**: Users can create AV-related threads to engage with the AV community. This allows users to stay notified of the latest technology and updates on AVs.<br>
4. **Safety Records**: Live updates are displayed to inform users of national accident rates of AVs, emergency response times, and accident reports on national roads. This helps users keep informed and ensures transparency on AV's safety.<br>
5. **Safety Resources**: Allows users to view troubleshooting information on possible issues that could arise. This ensures that AV users have efficient access to such information.<br>

## How to run

### Create and activate virtual environment
```python -m venv myenv``` <br>
For windows
```myenv\Scripts\activate``` <br>
For MAC/Linux
```source myenv/bin/activate``` <br>

### Install required packages
```pip install -r requirements.txt```

### To run Flask server
```python AVConnect.py```