# Digital Twin Testbed

This repository contains the supplementary source code, models, and documentation associated with the digital twin (DT) testbed presented in the article:

> Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.

By making the models and source code available in this repository, the authors aim to support reuse, adaptation, and further development by other researchers and educators (in accordance with the applicable licenses of this project and third-party components).

---

## Testbed Description

The testbed consists of a **LEGO®-based gantry robot** for automated material transport and **interactive workstations** for human-DT interaction. Both physical and digital components are connected through a containerized software architecture based on [Docker](https://github.com/docker) and [FastAPI](https://github.com/fastapi/fastapi).  

![Overview of the digital twin testbed.](/resources/digital-twin-testbed-overview.jpg)

*Overview of the modular DT testbed, consisting of the gantry robot and two interactive workstations. The tablet (optional) displays the gantry robot’s web-based UI served via a FastAPI endpoint that is accessible from any device on the WLAN.*

The testbed enables the development and evaluation of DT systems for construction management, including status monitoring, control interfaces, distributed services, data logging, edge computing, and human-digital-twin interaction. Its modular design allows components, databases, and interaction technologies to be exchanged or extended for different scenarios.  

---

## Requirements
 

### Hardware

The following hardware components are recommended for building and operating the testbed.

**Gantry Robot**

| Item | URL |
|---|---|
| Raspberry Pi 5 (8 GB) | https://www.raspberrypi.com/products/raspberry-pi-5/
| Raspberry Pi Build Hat | https://www.raspberrypi.com/products/build-hat/
| Raspberry Pi Build Hat Power Supply | https://www.raspberrypi.com/products/build-hat-power-supply/
| microSD card (64 GB) | https://www.raspberrypi.com/products/sd-cards/
| LEGO® Large Angular Motor (4x) | https://www.bricklink.com/v2/catalog/catalogitem.page?S=88017-1

**Interactive Workstation**

| Item | URL |
|---|---|
| Raspberry Pi 5 (8 GB) | https://www.raspberrypi.com/products/raspberry-pi-5/
| microSD card (64 GB) | https://www.raspberrypi.com/products/sd-cards/
| Raspberry Pi 7-inch Touch Display | https://www.raspberrypi.com/products/touch-display-2/
| Raspberry Pi Power Supply | https://www.raspberrypi.com/products/27w-power-supply/

### Software

For software requirements, see the dedicated `README` file in the `code/` folder.

To view and edit the digital brick models, we recommend using the [BrickLink Studio](https://www.bricklink.com/v3/studio/download.page) software.

---

## Repository Contents

```text
Digital-Twin-Testbed/
├── code/                       # Contains the source code for operating the gantry robot (has separate README file)
├── licenses/                   # License information
├── models/                     
    ├── 3d-print-main/          # STL file of the custom-designed claws; created by the authors of this publication
    ├── 3d-print-third-party/   # STL file of the custom-designed container that houses the Raspberry Pi computer; re-used from a third party (see license information below)    
    ├── bricks-main/            # Digital model of the gantry robot and rails components; created by the authors of this publication
    ├── bricks-third-party/     # Digital model of a few gantry robot and rail components; re-used from a third party (see license information below)    
├── resources/                  # Images used in this documentation
├── README.md                   # This file
```

---

## License

The contents of this repository are distributed under different licenses to separate source code, images and 3D models. See the corresponding license files in the `licenses/` directory for full license texts.

| Content | Path | License |
|---|---|---|
| Source code (.py, .js, .html, .css) | `code/` | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](licenses/MIT) |
| Main LEGO® and 3D printing models | `models/3d-print-main/`, `models/bricks-main/` | [![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-blue.svg)](licenses/CC-BY-4.0.txt) |
| Adapted third party LEGO® components | `models/bricks-third-party/` | [![License: Proprietary, education purposes only](https://img.shields.io/badge/License-Education%20purposes%20only-lightgrey)](licenses/Education-Purposes.txt) |
| Adapted third party 3D printing components | `models/3d-print-third-party/` | [![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-blue.svg)](licenses/CC-BY-NC-SA-4-0.txt) |
| Images, Logos | `resources/`, `code/fastapi/app/templates/assets/img/` | [![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC_BY--NC--SA_4.0-blue.svg)](licenses/CC-BY-NC-SA-4-0.txt) |

The gantry robot design includes a few LEGO® components that are based on an existing Rebrickable® MOC (https://rebrickable.com/mocs/MOC-119580/Mr_Jos/4d-gantry-robot-superfast-basic-setup/ by the user 'Mr_Jos' - Jozua van R.). These elements are provided in the separate file `gantry-robot-third-party.ldr` and their creator Jozua van R. gave permission that they can be re-used for education purposes. 

The custom-designed container that houses the Raspberry Pi computer is based on an existing model (https://www.thingiverse.com/thing:3713324/files by the user 'paulirotta'). This model is provided in the separate .stl file `housing-container-third-party.stl` and is licensed under CC BY-NC-SA 4.0.

The rest of the gantry robot design, the complete source code and accompanying documentation are own work by the authors of this publication: Irfan Čustović, Emilio Murillo Sierra, Ranjith K. Soman, Daniel M. Hall.

LEGO, the LEGO logo and BrickLink are trademarks of the LEGO Group of companies, which does not sponsor, authorize or endorse this research project. Raspberry Pi is a trademark of Raspberry Pi Ltd.

---

## Citation

If you use, display or make derivative works of the testbed or parts of it in academic or commercial projects, publications or software, please cite as:

```text
Čustović, I. et al. (2026). Experimenting with Digital Twins: a LEGO®-based Modular Testbed for Systematic Evaluation. EC3 Conference 2026. Corfu, Greece. Available at: https://doi.org/10.35490/EC3.2026.233.

```

BibTeX:

```bibtex
@inproceedings{custovicExperimentingWith2026,
  title = {Experimenting with {{Digital Twins}}: A {{LEGO}}\textregistered -Based {{Modular Testbed}} for {{Systematic Evaluation}}.},
  booktitle = {{{EC3 Conference}} 2026},
  author = {Irfan {\v C}ustovi{\'c} and Emilio Murillo Sierra and Ranjith K. Soman and Daniel M. Hall},
  year = 2026,
  month = jul,
  address = {Corfu, Greece},
  issn = {2684-1150},
  doi = {10.35490/EC3.2026.233},
  organisation = {European Council on Computing in Construction}
}
```

---

## Disclaimer

This project and all related materials are provided **“as is”**, without warranty of any kind. Use, modification, construction, operation, or reliance on this project or any derived setup is entirely at your own risk.

The authors, maintainers, contributors, and copyright holders are not responsible for any damage, accident, injury, loss, or liability arising from the use or misuse of this project, including any rebuilt, modified, or deployed setup based on it.

You are solely responsible for ensuring that your use complies with applicable laws, regulations, safety standards, and local requirements. Nothing in this disclaimer limits liability where such limitation is not permitted by applicable law.

---

## Contact

Irfan Čustović | [i.custovic@tudelft.nl](mailto:i.custovic@tudelft.nl) | Delft University of Technology, The Netherlands

Ranjith K. Soman | [r.soman@tudelft.nl](mailto:r.soman@tudelft.nl) | Delft University of Technology, The Netherlands


---

## Funding

This work was carried out within the project “[Smart Mobile Factory for Infrastructure Projects (SMF4INFRA)](https://www.smf4infra.net)” and supported by the [Swiss National Science Foundation [grant no. 204852]](https://data.snf.ch/grants/grant/204852).