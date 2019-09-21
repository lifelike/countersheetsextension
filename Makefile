docimages: doc/counter_symbols-1.png \
	doc/counter_symbols-2.png \
	doc/counters_size_list.png

svgtests:
	svgtests/run.sh

doc/counter_symbols-%.png: svgtests/bitmaps/counters_symbol_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_000%.png
	cp -v $^ $@

doc/counters_size_list.png: svgtests/bitmaps/counters_size_list.csv-template-counters.svgO_0_f_90_r_0.svgcs_layer_0001.png
	cp -v $^ $@

.PHONY: docimages svgtests
