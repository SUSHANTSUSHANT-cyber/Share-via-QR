# AISIN Secure File Transfer

## Overview

This project provides the Phase 1 foundation for an internal enterprise web application that will eventually support secure QR-based file transfer from personal devices to corporate systems.

## Architecture Summary

The planned flow is:

- Personal device uploads files through a simple web interface.
- A FastAPI backend processes requests.
- Microsoft Graph API and SharePoint Online are planned for later phases.
- Corporate users can access the transfer state through a browser-based experience.

## Technology Stack

- Python 3.12
- FastAPI
- Jinja2
- HTML5 and CSS3
- Vanilla JavaScript
- Pydantic

## Folder Structure

The project is organized into modular directories for configuration, routes, services, models, utilities, templates, and static assets.

## Setup Instructions

1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run the application:
   - `uvicorn app:app --reload`

## Running the Project

The development server will serve the landing page at the public URL configured in `SERVER_URL`.

## Development Roadmap

Phase 1 is focused on creating a clean and maintainable project skeleton. Future phases may introduce QR workflows, Graph API integration, SharePoint storage, and session management.
