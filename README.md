# TEMdb

This repository contains a data management system designed to handle data related to the TilEM pipeline. The system manages metadata for specimens, blocks, cutting sessions, sections, regions of interest (ROIs), imaging sessions, acquisitions and tiles.

## Project Overview

### What It Models

- **Specimens**: Samples prepared for imaging. Each specimen can have multiple blocks.
  
- **Blocks**: Subdivisions of a specimen. Blocks represent specific physical portions of a specimen prepared for sectioning and imaging.
  
- **Cutting Sessions**: Sessions where blocks are sectioned into sections, which are then placed on different media types for imaging.
  
- **Sections**: Thin slices of a block that are imaged. Sections are placed on a medium like a grid or support film for imaging.
  
- **Regions of Interest (ROIs)**: Specific areas within section(s) defined for imaging. ROIs can be created and adjusted based on the imaging requirements.
  
- **Imaging Sessions**: Sessions where ROIs are imaged. Imaging sessions are associated with specific sections and they manage multiple ROIs.
  
- **Acquisitions**: Each acquisition refers to the process of capturing image data from an ROI.
  
- **Tiles**: Individual images captured during an acquisition. A series of tiles form a montage of the ROI.
