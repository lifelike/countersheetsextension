docimages: doc/counter_symbols-1.png \
	doc/counter_symbols-2.png \
	doc/counters_size_list.png \
	doc/markers_list.png \
	doc/standees_20x20.png \
	doc/standees_20x35.png \
	doc/image_counters.png \
	doc/counters-2sides.csv-counters.svg.png \
	doc/counters-2sides.csv-counters.svgR_true.png \
	doc/counters-2sides.csv-counters.svgR_true.png \
	doc/counters-2sides.csv-counters.svgD_true_R_true_back.png \
	doc/counters-2sides.csv-counters.svgD_true_back.png \
	doc/counters-2sides.csv-counters.svg_back.png

svgtests:
	svgtests/run.sh

doc/counter_symbols-%.png: svgtests/bitmaps/counters_symbol_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_000%.png
	cp -v $^ $@

doc/counters_size_list.png: svgtests/bitmaps/counters_size_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_0001.png
	cp -v $^ $@

doc/markers_list.png: svgtests/bitmaps/markers_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_0001.png
	cp -v $^ $@

doc/standees_20x20.png: svgtests/bitmaps/standees.csv-standees.svgO_0_R_true.svgcs_layer_0001.png
	cp -v $^ $@

doc/standees_20x35.png: svgtests/bitmaps/standees.csv-standees.svgO_0_R_true.svgcs_layer_0002.png
	cp -v $^ $@

doc/image_counters.png: svgtests/bitmaps/image_counters.csv-template-counters.svgcs_layer_0001.png
	cp -v $^ $@


doc/counters-2sides.csv-counters.svg.png: svgtests/bitmaps/counters-2sides.csv-counters.svgcs_layer_0001.png
	cp -v $^ $@

doc/counters-2sides.csv-counters.svgD_true_back.png: svgtests/bitmaps/counters-2sides.csv-counters.svgD_true.svgcs_layer_0001_back.png
	cp -v $^ $@

doc/counters-2sides.csv-counters.svg_back.png: svgtests/bitmaps/counters-2sides.csv-counters.svgcs_layer_0001_back.png
	cp -v $^ $@

doc/counters-2sides.csv-counters.svgR_true.png: svgtests/bitmaps/counters-2sides.csv-counters.svgR_true.svgcs_layer_0001.png
	cp -v $^ $@

doc/counters-2sides.csv-counters.svgD_true_R_true_back.png: svgtests/bitmaps/counters-2sides.csv-counters.svgD_true_R_true.svgcs_layer_0001_back.png
	cp -v $^ $@

.PHONY: docimages svgtests
