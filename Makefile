docimages: doc/counter_symbols-1.png \
	doc/counter_symbols-2.png \
	doc/counters_size_list.png \
	doc/markers_list.png \
	doc/standees_20x20.png \
	doc/standees_20x35.png

svgtests:
	svgtests/run.sh

doc/counter_symbols-%.png: svgtests/bitmaps/counters_symbol_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_000%.png
	cp -v $^ $@

doc/counters_size_list.png: svgtests/bitmaps/counters_size_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_0001.png
	cp -v $^ $@

doc/markers_list.png: svgtests/bitmaps/markers_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_0001.png
	cp -v $^ $@

doc/standees_20x20.png: svgtests/bitmaps/standees.csv-standees.svgcs_layer_0001.png
	cp -v $^ $@

doc/standees_20x35.png: svgtests/bitmaps/standees.csv-standees.svgcs_layer_0002.png
	cp -v $^ $@

.PHONY: docimages svgtests
