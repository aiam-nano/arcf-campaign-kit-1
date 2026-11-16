# Laboratory handbook: composites development laboratory

This handbook describes the laboratory you are working in, the materials in stock, how to make and characterise batches with the `vlab` command, and the known characteristics of each instrument. Run `vlab help` for the command syntax and `vlab catalogue` for the materials in stock, their supplier datasheets, prices and the product specification.

## The resin system and processing

The matrix is a diglycidyl ether of bisphenol A (DGEBA) epoxy cured with isophorone diamine (IPDA). The amine ratio (`--amine`) is the nominal ratio of amine hydrogen equivalents to epoxy equivalents in the resin and hardener as weighed; 1.00 is stoichiometric. The neat cured resin has a density of 1.20 g cm⁻³. The supplier's recommended cure schedule is 2 h at 80 °C followed by 2 h at 120 °C, which is also the `vlab` default. The glass transition temperature an epoxy network can reach is limited by the temperature at which it is cured, because the reaction slows sharply once the network vitrifies; post-cure temperature and time therefore matter.

Fillers are dispersed directly in the resin. Probe sonication (`--sonic`, energy in kJ per gram of filler) and three-roll milling (`--passes`) are available, alone or together. Surface treatments are applied to the filler before dispersion: an epoxy-functional silane coupling agent, or a non-covalent aromatic dispersant. Graphene oxide (GO) is made in-house and must be thermally reduced before use; `--reduce` sets the reduction temperature.

Air entrained during mixing is removed by vacuum degassing. The mix can be degassed before the hardener is added (`--degas-stage pre`), when there is no pot-life limit but some air is re-entrained when the hardener is stirred in, or after (`--degas-stage post`), when the pot life of the mixed system limits how long degassing can last. The pot life is about 90 minutes at 25 °C and roughly halves for every 12–13 °C rise in temperature; a mix degassed beyond its pot life gels in the chamber and the batch is lost. Each batch produces enough plates for all tests.

## Laboratory time, credits and the log

Every action costs credits and laboratory time: making a batch takes one day, and each test a fraction of a day. The budget and the cost rules are in `vlab catalogue`. `vlab log` shows the laboratory log up to the current day, including deliveries, instrument service and ambient conditions. Production starts on day 20 and uses the stock in store on that day; your submission can only be sealed from day 20 (use `vlab wait` if you finish early). Every action is recorded in a signed ledger in `.vlab/`, and every data file in `lab_data/` is recorded by hash; neither may be edited.

## Instruments and data reduction

All data files are CSV with `#` metadata lines at the top. No instrument reports a finished property value; you reduce the raw data yourself.

**Tensile testing** (ISO 527-2 type 1A, clip-on extensometer). Force against extensometer strain to fracture, with each specimen's width and thickness. ISO 527-1 defines the modulus as the slope of stress against strain between 0.05 % and 0.25 % strain; the regression method is preferred.

**Fracture toughness** (ASTM D5045, single-edge-notched bend, span S = 4W). Load against displacement, with each specimen's W, B and measured initial crack length a. The materials here fail in a linear-elastic, brittle manner, so the maximum load can be taken as P_Q. With x = a/W, K_Q = P_Q / (B W^½) × f(x), where f(x) = 6 x^½ [1.99 − x(1 − x)(2.15 − 3.93x + 2.7x²)] / [(1 + 2x)(1 − x)^{3/2}]; with P in kN and B and W in cm, K_Q is in MPa m^½.

**DSC** (heat-flux, 10 K min⁻¹). Two heating scans of a specimen from the batch; heat flow is plotted exotherm up. The first scan shows the material as cured, including any residual cure exotherm; the second shows it after the first scan has completed the cure. The specification uses the midpoint of the glass-transition step on the first scan. Temperature calibration should be verified with the indium standard (`vlab test dsc-indium`, certified onset 156.60 °C) periodically and after any service.

**DMA** (single cantilever, 1 Hz). Storage and loss modulus and tan δ against temperature. The tan δ peak usually lies about 8–15 K above the DSC midpoint Tg.

**TGA.** Composite chips are run in nitrogen (the resin leaves about 10 % char); powders are run in air.

**Raman** (532 nm). Raw spectra without baseline subtraction, from composites or powders. The D, G and 2D bands of graphitic carbon are at about 1350, 1580 and 2700 cm⁻¹; the shape of the 2D band changes with the number of layers.

**Powder XRD** (Cu Kα, 0.15406 nm). Instrumental broadening is 0.08° (FWHM). Crystallite thickness can be estimated from the (002) reflection with the Scherrer equation.

**Nitrogen sorption** (77 K, powders only). Adsorption isotherm. Use the BET equation in the usual relative-pressure range of 0.05–0.30; 1 cm³ STP of nitrogen in a monolayer covers 4.353 m².

**Density** (Archimedes, deionised water). Mass in air and apparent mass in water for each piece, with the water temperature. Take the density of water as 0.99820 − 0.00021 (T − 20) g cm⁻³ between 20 and 25 °C.

**Electrical resistance.** Specimens are 50 × 10 × 4 mm bars with silver-painted electrodes on the end faces. The two-terminal method (voltage source, electrometer) measures the whole bar including the resistance of the painted contacts, which is typically 10³–10⁵ Ω and varies from bar to bar; it is reliable when the specimen resistance is much larger than this. The four-terminal method passes current through the end contacts and measures the voltage between two probes 20.0 mm apart on the top face, removing contact resistance; it is limited by the 100 V compliance of the current source and the 10¹⁰ Ω input impedance of the voltmeter, and readings flagged COMPLIANCE are invalid. The specification refers to the true volume resistivity of the material.

**Rheometry** (parallel plates). Steady-shear flow curve of the uncured mix of a batch, sampled immediately after dispersion, at a temperature you choose.

**SEM fractography.** Automated image analysis of tensile fracture surfaces over 4 mm², reporting agglomerate density and size and void area, with a qualitative comment.
