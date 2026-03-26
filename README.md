# 📈 Solomon Tensile Suite v1.9.1
**Advanced Mechanical Property Analytics & Constitutive Modeling for Bioplastics**

![Solomon Tensile Suite Logo](https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png)

## 📋 Overview
The **Solomon Tensile Suite** is a high-fidelity analytical framework engineered for Material Scientists and Mechanical Engineers. While optimized for biodegradable polymers—specifically **PBAT** and **PBAT/PLA blends**—it provides a robust solution for the "premature termination" problem common in high-elongation testing. 

By utilizing advanced linear extrapolation of the drawing plateau, the suite bridges the gap between empirical laboratory data and theoretical failure points, ensuring a comprehensive characterization of mechanical performance.

## 🚀 Key Features
* **Precision Extrapolation:** High-fidelity linear modeling of the plastic flow (drawing) region for samples that exceed equipment stroke limits.
* **Automated Analytics:** Instant extraction of **Young’s Modulus ($E$)**, **Yield Strength ($\sigma_y$)**, and **Toughness (Work of Fracture)**.
* **Scientific Visualization:** Interactive stress-strain plots with localized "Zoom Insets" for elastic region verification.
* **Professional Reporting:** One-click export to branded Excel reports containing raw data, summary metrics, and embedded high-resolution graphs.
* **Custom Metadata:** Organize research with Project Name, Batch ID, and Experimental Date tracking.

[Image of a stress-strain curve showing the elastic region, yield point, and plastic deformation plateau]

## 🛠️ Technical Methodology
1.  **Elastic Modulus:** Calculated via linear regression of the initial Hookean region (user-definable, typically 0.2%–1.0% strain).
2.  **Yield Detection:** Implements a smoothed-derivative algorithm to identify the transition from elastic to viscoplastic behavior, effectively filtering electronic signal noise.
3.  **Drawing Plateau Modeling:** Uses a Least-Squares fit of the final $n$ data points to project behavior up to a target deformation, with optional Gaussian noise injection for real-world simulation.

## 📦 Installation & Local Deployment
To run this suite locally, ensure you have Python 3.9+ installed, then:

1. Clone the repository:
   ```bash
   git clone [https://github.com/12solo/Tensile-test-extrapolator.git](https://github.com/12solo/Tensile-test-extrapolator.git)
   cd Tensile-test-extrapolator
