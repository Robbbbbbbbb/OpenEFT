# ATF only requires slaps and thumbs. The app is not currently set up to build a 10-roll plus slaps. Just know you can only use these for eForms.

from collections import namedtuple

OCRLocation = namedtuple("OCRLocation", ["id", "bbox", "fp_number"])
OCR_LOCATIONS = [ 
# Not right locations #    OCRLocation("last_name", (7248,668,2581,468),0),
# Not right locations #    OCRLocation("first_name", (12674,668,2581,468),0),
# Not right locations #    OCRLocation("middle_name", (9954,668,2581,468),0),
# Not right locations #    OCRLocation("signature", (60,1770,6904,354),0),
# Not right locations #    OCRLocation("date", (60,3710,594,354),0),
# Not right locations #    OCRLocation("residence", (60,1184,3488,468),0),
# Not right locations #    OCRLocation("reason", (60,6045,6879,468),0),
# Not right locations #    OCRLocation("aliases", (7307,1794,3046,1152),0),
# Not right locations #    OCRLocation("citizenship", (7242,3318,3516,328),0),
# Not right locations #    OCRLocation("ssn", (7242,5950,3516,328),0),
# Not right locations #    OCRLocation("dob", (16266,2710,2832,288),0),
# Not right locations #    OCRLocation("pob", (16270,3338,2824,348),0),
# Not right locations #    OCRLocation("sex", (10842,3260,655,429),0),
# Not right locations #    OCRLocation("race", (11582,3338,608,348),0),
# Not right locations #    OCRLocation("height", (11582,3338,1072,348),0),
# Not right locations #    OCRLocation("weight", (11582,3338,772,348),0),
# Not right locations #    OCRLocation("eyes", (11582,3338,836,348),0),
# Not right locations #    OCRLocation("hair", (11582,3338,760,348),0),
#    OCRLocation("R_THUMB", (90,7103,3700,3580), 1),
#    OCRLocation("R_INDEX", (3884,7103,3835,3580), 2),
#    OCRLocation("R_MIDDLE", (7753,7103,3796,3580), 3),
#    OCRLocation("R_RING", (11583,7103,3836,3580), 4),
#    OCRLocation("R_LITTLE", (15453,7103,3658,3580), 5),
#    OCRLocation("L_THUMB", (90,10717,3700,3580), 6),
#    OCRLocation("L_INDEX", (3884,10717,3835,3580), 7),
#    OCRLocation("L_MIDDLE", (7753,10717,3796,3580), 8),
#    OCRLocation("L_RING", (11583,10717,3836,3580), 9),
#    OCRLocation("L_LITTLE", (15453,10717,3658,3580), 10),
#    OCRLocation("R_THUMB2", (9653,14317,1866,4634), 11),
#    OCRLocation("L_THUMB2", (7753,14317,1866,4634), 12),
    OCRLocation("R_FOUR", (11583,14317,7559,4634), 13),
    OCRLocation("L_FOUR", (90,14417,7559,4634), 14),
    OCRLocation("2_THUMBS", (7753,14317,3795,4634), 15), # Consolidate into 1 record
]
