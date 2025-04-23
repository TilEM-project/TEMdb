# Welcome to TEMdb Documentation

This site contains documentation for the TEMdb Microscopy Pipeline Database, a system designed to manage complex metadata associated with Electron Microscopy (EM) imaging workflows.

## Purpose

Modern microscopy pipelines generate vast amounts of data and associated metadata across multiple preparation and imaging steps. TEMdb aims to:

* **Centralize Metadata:** Provide a single source of truth for tracking samples from initial specimen preparation through to final image tile acquisition.
* **Standardize Information:** Define clear schemas for different stages of the pipeline, ensuring consistency.
* **Facilitate Data Tracking & Querying:** Enable users and automated systems to easily find and retrieve information about specific specimens, sections, ROIs, or acquisitions.
* **Support Automation:** Offer a robust FastAPI backend for programmatic interaction with the database.

## Core Data Workflow

TEMdb models the typical flow of a sample through the Sectioning and Imaging pipeline:

1.  **[Specimen](models/Specimen.md):** The initial biological sample that is prepared.
2.  **[Block](models/Block.md):** The specimen may be processed into one or more blocks suitable for sectioning. MicroCT scans might occur at this stage.
3.  **[Cutting Session](models/CuttingSession.md):** A block undergoes sectioning during a specific session, using a particular device.
4.  **[Section](models/Section.md):** Thin sections are cut from the block and placed onto a medium (like tape or a grid). Each section has a number and associated quality metrics.
5.  **[Substrate](models/Substrate.md):** The physical medium (wafer, tape, grid, etc.) that holds sections. Contains information about apertures, reference points, and substrate status.
6.  **[ROI (Region of Interest)](models/ROI.md):** Specific areas on one or more sections are identified for high-resolution imaging. Parent/child relationships can define sub-regions.
7.  **[Acquisition Task](models/AcquisitionTask.md):** A task is created to manage the imaging of a specific ROI with status tracking.
8.  **[Acquisition](models/Acquisition.md):** The actual imaging process for an ROI occurs, capturing hardware settings, calibration info, and resulting collection of image data.
9.  **[Tile](models/Tile.md):** Individual image frames (tiles) are captured during an acquisition, forming a montage. Each tile has associated metadata like position and quality score metrics and file path.

## Technical Overview

* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python web framework)
* **Database:** [MongoDB](https://www.mongodb.com/) (NoSQL document database)
* **ODM:** [Beanie](https://beanie-odm.dev/) (Asynchronous Python ODM for MongoDB based on Pydantic)
* **Deployment (Local):** [Docker Compose](https://docs.docker.com/compose/)

## Navigating This Documentation

* **Schema Diagrams:** Visualize the relationships between data models:
    * [Preparation Workflow Diagram](./schema_Preparation_erd.md)
    * [Imaging Workflow Diagram](./schema_Imaging_erd.md)
* **Models:** Detailed descriptions of each data model (schema) can be found in the "Models" section of the navigation.
* **API Reference:** Explore the available API endpoints:
    * [Interactive API (Swagger)](api_swagger.md)
    * [Alternative API (ReDoc)](api_redoc.md)
## Getting Started (Local Development)

Refer to the `docker-compose.yml` file and the project's main `README.md` for instructions on setting up and running the TEMdb application and database locally using Docker.
