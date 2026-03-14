This project aims to create a Claude AI skill that will assist in creating Kicad schematics.

The goal is to that it shall be possible to first brainstorm a design based on requirement inputs, then have Claude create the schematics.
You shall record relevant steps done in these project discussions so to that these can assist when creating the skill. However, the actual design decisions are not relevant to the skill, but the process of getting there might be.

Workflow for the skill shall be:
* Agree on Top Level requirements
  - what the design should should be able to do
  - set interfaces
  - avaiable power
  - references for CPU, HMI etc
  - Propose relevant harmonized standards that can be applicable to the project
   - Include reference links to an abstract of the document.
  - OUTPUT: an .md file of the requirements and ask if a pdf should be generated.
  
 * Decide on main architecture as this will affect the block level design
  - What MCU / CPU system (if any)
  - Any real time requirements?
  - Any forseeable memeory requirements? Size / speed?
  - CPU system power requirements, are there any issues?
  - CPU system cost
  - OUTPUT: an .md file on the chosen system and the rational behind it and ask if a pdf-report should be generated.
  
 * Claude should then be able to propose a block level design for review
  - Blocks shall be kept small and be able to implement in a hierarchy fashion
  - OUTPUT: an .md file on the architechure and the rational behind it and ask if a pdf-report should be generated.
  
 * After review of each block:
  - Propose components, taking into account price and availability. LSSC partnumbers shall be considered and avaialble for all components that are proposed.
  - Together with the user select components for each block.
  - OUTPUT: an .md file on the chosen components and the rational behind it, including components that have been reviewed and discarded (with reasons why they were not selected). Ask if a pdf should be generated
  
 * After completed review, create a BOM highlighting which components are available in Kicad standard libraries and which components are missing
  - OUTPUT: .csv file suitable for import in Excel with information on LSCS partnumbers and availability.
  
 * Kicad Project Structure
  - For the missing components, download these using easycad2kicad skill. No componnes may be created "by hand" in this stage.
    - Name the new libraries after the project name.
    - Make sure that both the symbol library and footprint library is added to the project file and that they only contain the relevant components.
  - Start a kicad project asking for Project name, Author name, company name and logo and add these to the project schematics.
  - Create schematics pages for the blocks and create the (empty) hierarchy schematic sheet entries
  
 * For each block in the design
  - Using the python scripts to generate schematics from the traincontrol project as templates, copy these and modify them for more generic use in the future skill. 
  - Populate the schematics with the relevant components
  - Add wirestubs and netnames
  - Add sheet label entries, and update the parent sheet symbol.
  
 * Project verification
  - 

