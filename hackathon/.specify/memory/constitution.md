<!--
Sync Impact Report:
Version change: old → 1.0.0
Modified principles: Preamble, Core Objectives, Quarter Timeline & Modules, The Capstone Project, Tech Stack & Tools.
Added sections: Course Code, Theme, Mission, Preamble, Article I, Article II, Article III, Article IV.
Removed sections: SECTION_2_NAME, SECTION_3_NAME.
Templates requiring updates:
- .specify/templates/plan-template.md: ⚠ pending
- .specify/templates/spec-template.md: ⚠ pending
- .specify/templates/tasks-template.md: ⚠ pending
- .specify/templates/commands/*.md: ⚠ pending
Follow-up TODOs: None
-->
# Constitution of Physical AI & Humanoid Robotics

## Course Overview
**Course Code**: PAI-400
**Theme**: AI Systems in the Physical World & Embodied Intelligence
**Mission**: To bridge the gap between the digital brain and the physical body.

## Preamble
We hold these truths to be self-evident: that intelligence is not strictly digital, but must be embodied to truly understand the world. The future of AI extends beyond servers and screens into the physical realm. In this quarter, students will transition from coding agents in a void to architecting Physical AI—systems that function in reality, respect the laws of physics, and interact with humans naturally.

## Article I: Core Objectives
### Embodiment
To grant AI agents a physical form (chassis, sensors, actuators) allowing them to manipulate the world.

### Simulation-to-Reality (Sim2Real)
To master the art of the "Digital Twin," training in risk-free virtual environments before deploying to hardware.

### Cognitive Control
To utilize Large Language Models (LLMs) not just for text, but as the high-level planning cortex for robotic motor function.

## Article II: Quarter Timeline & Modules
### Module 1: The Robotic Nervous System (ROS 2)
"The body must obey the mind." This module establishes the fundamental communication infrastructure required to control complex hardware.
**Focus**: Middleware for robot control and inter-process communication.
**Key Concepts**: Nodes & Topics: The publish-subscribe architecture of robot data. Services & Actions: Request/response patterns for blocking and non-blocking tasks. rclpy: Bridging high-level Python AI agents to low-level motor controllers. URDF (Unified Robot Description Format): Defining the kinematics, joints, and visual geometry of a humanoid robot.

### Module 2: The Digital Twin (Gazebo & Unity)
"Training in the matrix." Before a robot walks in the real world, it must fall a thousand times in the simulation.
**Focus**: Physics simulation, environment building, and sensor emulation.
**Key Concepts**: Physics Engines: Simulating gravity, friction, inertia, and collisions in Gazebo. High-Fidelity Rendering: Using Unity for photorealistic human-robot interaction scenarios. Sensor Simulation: Implementing virtual LiDAR, Depth Cameras, and IMUs (Inertial Measurement Units) to generate noisy, realistic data streams.

### Module 3: The AI-Robot Brain (NVIDIA Isaac™)
"Perception precedes action." A robot must map its environment to navigate it effectively.
**Focus**: Advanced perception, synthetic data generation, and navigation.
**Key Concepts**: NVIDIA Isaac Sim: Leveraging photorealism to generate synthetic training data for computer vision models. Isaac ROS: utilizing hardware acceleration for VSLAM (Visual Simultaneous Localization and Mapping). Nav2 Stack: Implementing path planning algorithms (A*, Dijkstra) specifically tuned for bipedal humanoid movement constraints.

### Module 4: Vision-Language-Action (VLA)
"From words to motion." The convergence of Generative AI and Robotics.
**Focus**: The intersection of LLMs, Vision Transformers, and Control Theory.
**Key Concepts**: Voice-to-Action: Integrating OpenAI Whisper to process auditory commands. Cognitive Planning: Utilizing LLMs (e.g., GPT-4o, Llama 3) to decompose abstract commands ("Clean the room") into a structured sequence of ROS 2 primitives (Locate Object -> Plan Path -> Grasp -> Transport). VLA Models: End-to-end models that output robot actions directly from visual and textual inputs.

## Article III: The Capstone Project
**Objective**: Students will deploy a full-stack Physical AI system in a high-fidelity simulated environment (household or warehouse). The robot must operate autonomously based on a high-level human request.
**The Workflow**: Input: The robot receives a voice command (e.g., "Find the red medical kit and bring it to the couch"). Perception (Whisper + LLM): The system transcribes audio and parses the intent into a task list. Navigation (Isaac ROS + Nav2): The robot generates a map, localizes itself, and plans a path to the target area while avoiding dynamic obstacles. Vision (YOLO/Transformer): The robot identifies the specific object using computer vision. Manipulation (MoveIt): The robot executes inverse kinematics to grasp the object. Completion: The robot navigates to the destination and places the object.

## Article IV: Tech Stack & Tools
**Operating System**: Ubuntu Linux (22.04 LTS)
**Middleware**: ROS 2 (Humble Hawksbill)
**Languages**: Python (Logic/AI), C++ (Performance Nodes)
**Simulation**: Gazebo Fortress, Unity, NVIDIA Isaac Sim
**AI/ML**: PyTorch, OpenAI API, Hugging Face Transformers

## Governance
This constitution outlines the foundational principles and structure of the Physical AI & Humanoid Robotics course (PAI-400). Amendments will be made through instructor discretion and course committee review.

**Version**: 1.0.0 | **Ratified**: 2025-11-28 | **Last Amended**: 2025-11-28
