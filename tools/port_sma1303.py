#!/usr/bin/env python3
"""Convert the A31 SMA1303 amplifier driver from the snd_soc_codec API (4.14)
to snd_soc_component (4.18+). Mechanical, same conversion upstream used."""
import re
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text()

# remove(): component .remove returns void
s = s.replace("static int sma1303_remove(struct snd_soc_codec *codec)",
              "static void sma1303_remove(struct snd_soc_codec *codec)", 1)
m = re.search(r"static void sma1303_remove\(struct snd_soc_codec \*codec\)\n\{.*?\n\}", s, re.S)
body = m.group(0)
body2 = re.sub(r"\n\treturn 0;\n\}$", "\n}", body)
s = s.replace(body, body2, 1)

# driver struct: flatten component_driver, idle_bias_off -> idle_bias_on = 0
old_drv = re.search(r"static const struct snd_soc_codec_driver soc_codec_dev_sma1303 = \{.*?\n\};", s, re.S).group(0)
new_drv = """static const struct snd_soc_component_driver soc_codec_dev_sma1303 = {
	.probe = sma1303_probe,
	.remove = sma1303_remove,
	.suspend = sma1303_suspend,
	.resume = sma1303_resume,
	.controls = sma1303_snd_controls,
	.num_controls = ARRAY_SIZE(sma1303_snd_controls),
	.dapm_widgets = sma1303_dapm_widgets,
	.num_dapm_widgets = ARRAY_SIZE(sma1303_dapm_widgets),
	.dapm_routes = sma1303_audio_map,
	.num_dapm_routes = ARRAY_SIZE(sma1303_audio_map),
	.idle_bias_on = 0,
	.use_pmdown_time = 1,
	.endianness = 1,
	.non_legacy_dai_naming = 1,
};"""
s = s.replace(old_drv, new_drv, 1)

subs = [
    (r"\bsnd_soc_register_codec\b", "snd_soc_register_component"),
    (r"\bsnd_soc_unregister_codec\b", "snd_soc_unregister_component"),
    (r"\bsnd_soc_codec_get_drvdata\b", "snd_soc_component_get_drvdata"),
    (r"\bsnd_soc_kcontrol_codec\b", "snd_soc_kcontrol_component"),
    (r"\bsnd_soc_dapm_to_codec\b", "snd_soc_dapm_to_component"),
    (r"\bsnd_soc_codec_get_dapm\b", "snd_soc_component_get_dapm"),
    (r"\bdai->codec\b", "dai->component"),
    (r"\bcodec->component\.", "codec->"),
    (r"\bstruct snd_soc_codec\b", "struct snd_soc_component"),
]
for a, b in subs:
    s = re.sub(a, b, s)
assert "snd_soc_codec" not in s.replace("soc_codec_dev_sma1303", ""), \
    [l for l in s.splitlines() if "snd_soc_codec" in l][:5]
p.write_text(s)
print("sma1303.c converted to snd_soc_component")
