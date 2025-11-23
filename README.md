# **ParaInlet Application**

**Version:** 1.0

**Type:** Streamlit Web Application

**Domain:** Aerodynamics / Propulsion Engineering

## **1\. Installation & Execution**

### **1.1 Prerequisites**

* **Python:** Version 3.8 or higher is required.  
* **Pip:** Python package manager.

### **1.2 Setup Instructions**

1. **Save the File:** Ensure the source code is saved as inlet copy.py (or your preferred filename) in a local directory.  
2. **Install Dependencies:** Open your terminal or command prompt and run the following command to install the necessary libraries:  
   pip install streamlit pandas altair

### **1.3 How to Run**

Navigate to the folder containing your script in the terminal and execute:

streamlit run inlet.py

* The application will automatically launch in your default web browser.  
* The default local address is usually http://localhost:8501.  
* To stop the server, press Ctrl \+ C in your terminal.

## **2\. Overview**

**ParaInlet** is a web-based engineering tool designed to calculate and visualize aerodynamic performance metrics for aircraft air inlets (intakes). It allows users to model multiple inlet configurations simultaneously, compute efficiencies based on isentropic flow relations, and compare results through interactive visualizations.

### **2.1 Key Features**

* **Dynamic Modeling:** Support for analyzing 1 to 10 inlets simultaneously.  
* **State Persistence:** Retains data across UI interactions using Streamlit Session State.  
* **Physics Engine:** Calculates Total Pressure Recovery, Kinetic Energy Efficiency, Adiabatic Efficiency, and Distortion Index.  
* **Visualization:** Generates comparative bar charts using the Altair library.

## **3\. Dependencies**

The application requires the following Python libraries:

| Library | Purpose |
| :---- | :---- |
| streamlit | Core web framework and UI widgets. |
| pandas | Data manipulation and tabular display. |
| altair | Declarative statistical visualization for charts. |

## **4\. Architecture & Control Flow**

The application follows a procedural execution model typical of Streamlit scripts, re-running from top to bottom upon interaction.

### **4.1 Initialization Phase**

1. **Page Config:** Sets browser metadata (Title: "ParaInlet", Icon: "✈️") and enforces a "centered" layout optimized for mobile devices.  
2. **Session State:** Checks for the existence of the inlets key in st.session\_state. If missing, initializes it as an empty list.

### **4.2 Configuration & State Management**

The application dynamically resizes the data model based on user input:

* **Input:** User selects num\_inlets (Integer 1-10).  
* **Expansion Logic:** If num\_inlets \> current list size, new default inlet dictionaries are appended.  
* **Reduction Logic:** If num\_inlets \< current list size, the list is sliced to remove excess entries.

### **4.3 Data Structure**

Each inlet is stored as a dictionary with the following schema:

| Key | Type | Description | Default |
| :---- | :---- | :---- | :---- |
| name | String | Identifier for the inlet | "Inlet N" |
| gamma | Float | Specific heat ratio ($\\gamma$) | 1.4 |
| mach | Float | Free stream Mach number ($M\_i$) | 2.0 |
| pr\_th | Float | Theoretical Pressure Recovery limit | 0.98 |
| pt\_i, pt\_e | Float | Total Pressure (Inlet/Exit) \[Pa\] | 101325, 95000 |
| pt\_max/min/avg | Float | Distortion pressures \[Pa\] | Various |
| tt\_i, tt\_e | Float | Total Temperatures \[K\] | 300, 350 |
| t\_i, t\_e | Float | Static Temperatures \[K\] | 280, 330 |

## **5\. Component Reference**

### **5.1 Calculation Engine**

**Function:** calculate\_parameters(data)

Core physics engine that processes a single inlet's raw data dictionary and returns computed metrics.

**Computed Metrics:**

1. Total Pressure Recovery ($\\pi$):  
   $$\\pi \= P\_{t,e} / P\_{t,i}$$  
2. Kinetic Energy Efficiency ($\\eta\_{KE}$):  
   Derived from the deviation of actual kinetic energy at the exit compared to isentropic expansion.  
3. Adiabatic Compression Efficiency ($\\eta\_{comp}$):  
   Relates the isentropic temperature rise to the actual temperature rise.  
4. Distortion Index (DI):  
   $$DI \= (P\_{t,max} \- P\_{t,min}) / P\_{t,avg}$$  
5. Shock Efficiency ($\\eta\_{shock}$):  
   Ratio of actual recovery to theoretical recovery (pr\_th).

### **5.2 Visualization Engine**

**Function:** plot\_colored\_chart(df, x\_col, y\_col, title)

A wrapper around altair.Chart to generate consistent, color-coded bar charts.

* **Parameters:**  
  * df: Pandas DataFrame containing results.  
  * x\_col: Column name for X-axis (usually "Name").  
  * y\_col: Column name for Y-axis (metric to plot).  
  * title: Chart title string.  
* **Styling:** Uses mark\_bar() with distinct colors for every X value to ensure visual differentiation between inlets.

## **6\. User Interface (UI) Specification**

### **6.1 Input Section**

* **Tabs:** Uses st.tabs to organize inputs for multiple inlets without cluttering the screen.  
* **Key Generation:** Critical for stream operations. Every widget inside the loop is assigned a unique key (e.g., key=f"n{i}") to prevent ID collisions between different inlets.

### **6.2 Results Section**

Triggered by the "Calculate Results" button.

1. **Data Table:** Displays a st.dataframe styled with specific string formatting (e.g., 2 decimal places for percentages, 4 for ratios).  
2. **Charts:** Renders 5 vertical bar charts:  
   * Kinetic Energy Efficiency  
   * Adiabatic Efficiency  
   * Pressure Recovery  
   * Distortion Index  
   * Shock Efficiency

## **7\. Error Handling & Edge Cases**

* **Division by Zero:** The calculate\_parameters function includes guards (e.g., if data\["pt\_i"\] \!= 0\) to prevent runtime crashes when denominators (Input Pressure or Temperatures) are zero.  
* **Negative Inputs:** While not explicitly restricted in the UI min\_value, calculation logic checks for mach \> 0 and gamma \> 1 before attempting complex power calculations.

## **8\. Line-by-Line Code Analysis**

This section maps specific lines of code in inlet copy.py to their functional roles within the application.

### **8.1 Imports and Setup**

* **Lines 1-3:** Import necessary libraries: streamlit (UI), pandas (Data aggregation), and altair (Charting).  
* **Lines 6-10:** st.set\_page\_config defines the browser tab properties. layout="centered" is specifically chosen to optimize the mobile viewing experience.  
* **Lines 13-14:** Renders the main H1 title and a smaller caption below it.

### **8.2 State Initialization**

* **Lines 17-18:** Checks st.session\_state. If the key 'inlets' does not exist, it is initialized as an empty list. This step is mandatory in Streamlit to ensure data persists between button clicks and interactions.

### **8.3 Configuration Logic**

* **Lines 21-28:** Renders the "Setup" container. The number\_input widget allows the user to select between 1 and 10 inlets.  
* **Lines 31-48:** **Dynamic State Management.**  
  * Logic compares the user's requested num\_inlets against the current list length.  
  * **Expansion:** If the user increases the count, a loop appends new dictionaries with default values (Mach 2.0, Gamma 1.4, etc.).  
  * **Reduction:** If the user decreases the count, list slicing (\[:num\_inlets\]) removes the excess entries.

### **8.4 Input Rendering (The UI Loop)**

* **Lines 53-57:** st.tabs generates navigation tabs for each inlet. The code iterates through these tabs.  
* **Lines 60-87:** Renders input widgets for Flow, Pressure, and Temperature.  
  * **Critical Implementation Detail:** Every widget uses a dynamic key parameter (e.g., key=f"n{i}", key=f"g{i}"). This ensures Streamlit treats the "Gamma" input for Inlet 1 as a distinct entity from the "Gamma" input for Inlet 2\.

### **8.5 Calculation Engine**

* **Lines 91-133:** calculate\_parameters(data)  
  * **Lines 92-94:** Computes Pressure Recovery ($\\pi$).  
  * **Lines 97-106:** Computes Kinetic Energy Efficiency ($\\eta\_{KE}$) using complex isentropic flow formulas.  
  * **Lines 109-114:** Computes Adiabatic Efficiency ($\\eta\_{comp}$).  
  * **Lines 117-119:** Computes Distortion Index (DI).  
  * **Lines 126-133:** Returns a structured dictionary with keys formatted for the final display (e.g., "KE Eff (%)").

### **8.6 Visualization Logic**

* **Lines 135-143:** plot\_colored\_chart  
  * Defines a reusable Altair chart function.  
  * **Line 140:** color=alt.Color(x\_col, legend=None) is used to assign a unique color to each bar based on the inlet name, improving readability.

### **8.7 Main Execution Block**

* **Line 146:** if st.button(...): The entry point for processing. The code inside this block only executes when the user clicks "Calculate Results".  
* **Line 148:** A list comprehension runs calculate\_parameters on every item in st.session\_state.inlets.  
* **Line 149:** Converts the list of results into a Pandas DataFrame.  
* **Lines 153-162:** Renders the results table using df.style.format to ensure percentages and decimals are readable.  
* **Lines 166-171:** Calls plot\_colored\_chart five times to render the specific performance metrics.  
* **Lines 173-174:** Displays an informational prompt if the calculation button has not yet been clicked.