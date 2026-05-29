"""База пресетов чувствительности Free Fire (бесплатная выдача)."""

FF_SETTINGS_DB: dict = {
    "samsung": {
        "brands": ["samsung", "самсунг", "galaxy", "галакси"],
        "presets": [
            {
                "match": [
                    "a1", "a2", "a3", "a5", "a6", "a7", "a8", "a9", "a10", "a12", "a13", "a14", "a15",
                    "a20", "a21", "a22", "a23", "a24", "a25", "a30", "a31", "a32", "a33", "a34", "a35",
                    "a50", "a51", "a52", "a53", "a54", "a55", "a70", "a71", "a72", "a73",
                    "m12", "m13", "m14", "m21", "m22", "m31", "m32", "m51", "m52", "m53",
                ],
                "s": {
                    "general": 186, "red_dot": 148, "scope_2x": 152, "scope_4x": 172,
                    "awm": 82, "freelook": 50, "button": 52, "dpi": 635,
                },
            },
            {
                "match": [
                    "s8", "s9", "s10", "s20", "s21", "s22", "s23", "s24",
                    "note8", "note9", "note10", "note20", "s серия", "s10+", "s20+", "s21+", "s22+", "s23+",
                ],
                "s": {
                    "general": 195, "red_dot": 155, "scope_2x": 160, "scope_4x": 178,
                    "awm": 88, "freelook": 55, "button": 50, "dpi": 680,
                },
            },
            {
                "match": ["f12", "f13", "f14", "f22", "f23", "f34", "f41", "f42", "f54", "f62", "f63", "f серия"],
                "s": {
                    "general": 183, "red_dot": 145, "scope_2x": 150, "scope_4x": 168,
                    "awm": 80, "freelook": 48, "button": 53, "dpi": 620,
                },
            },
        ],
        "default": {
            "general": 186, "red_dot": 148, "scope_2x": 152, "scope_4x": 172,
            "awm": 82, "freelook": 50, "button": 52, "dpi": 635,
        },
    },
    "redmi": {
        "brands": ["redmi", "редми", "red mi"],
        "presets": [
            {
                "match": [
                    "note 8", "note 9", "note 10", "note 11", "note 12", "note 13",
                    "note8", "note9", "note10", "note11", "note12", "note13",
                ],
                "s": {
                    "general": 190, "red_dot": 152, "scope_2x": 156, "scope_4x": 175,
                    "awm": 85, "freelook": 52, "button": 51, "dpi": 650,
                },
            },
            {
                "match": [
                    "redmi 9", "redmi 10", "redmi 12", "redmi 13", "redmi9", "redmi10", "redmi12", "redmi13",
                    "9c", "9a", "10c", "12c",
                ],
                "s": {
                    "general": 184, "red_dot": 146, "scope_2x": 150, "scope_4x": 170,
                    "awm": 80, "freelook": 48, "button": 53, "dpi": 625,
                },
            },
            {
                "match": ["redmi k", "k20", "k30", "k40", "k50", "k60", "k70", "poco", "поко"],
                "s": {
                    "general": 200, "red_dot": 160, "scope_2x": 165, "scope_4x": 185,
                    "awm": 92, "freelook": 58, "button": 49, "dpi": 700,
                },
            },
        ],
        "default": {
            "general": 188, "red_dot": 150, "scope_2x": 154, "scope_4x": 173,
            "awm": 83, "freelook": 51, "button": 52, "dpi": 645,
        },
    },
    "xiaomi": {
        "brands": ["xiaomi", "ксиоми", "xiomi", "ксяоми", "mi "],
        "presets": [
            {
                "match": [
                    "mi 10", "mi 11", "mi 12", "mi 13", "xiaomi 12", "xiaomi 13", "xiaomi 14",
                    "12s", "13s", "12 pro", "13 pro", "14 pro",
                ],
                "s": {
                    "general": 198, "red_dot": 158, "scope_2x": 163, "scope_4x": 182,
                    "awm": 90, "freelook": 56, "button": 50, "dpi": 675,
                },
            },
            {
                "match": ["xiaomi 11i", "xiaomi 11 lite", "civi", "mi 9", "mi 8", "mi a", "play"],
                "s": {
                    "general": 185, "red_dot": 147, "scope_2x": 151, "scope_4x": 171,
                    "awm": 81, "freelook": 49, "button": 52, "dpi": 630,
                },
            },
        ],
        "default": {
            "general": 192, "red_dot": 153, "scope_2x": 157, "scope_4x": 176,
            "awm": 86, "freelook": 53, "button": 51, "dpi": 655,
        },
    },
    "poco": {
        "brands": ["poco", "поко", "poko"],
        "presets": [
            {
                "match": ["poco x3", "poco x4", "poco x5", "poco x6", "x3 pro", "x4 pro", "x5 pro", "x6 pro"],
                "s": {
                    "general": 202, "red_dot": 162, "scope_2x": 167, "scope_4x": 187,
                    "awm": 93, "freelook": 59, "button": 48, "dpi": 710,
                },
            },
            {
                "match": [
                    "poco m2", "poco m3", "poco m4", "poco m5", "poco m6",
                    "poco c3", "poco c4", "poco c5", "poco c6", "poco c65",
                ],
                "s": {
                    "general": 185, "red_dot": 147, "scope_2x": 152, "scope_4x": 172,
                    "awm": 82, "freelook": 49, "button": 52, "dpi": 632,
                },
            },
            {
                "match": ["poco f1", "poco f2", "poco f3", "poco f4", "poco f5", "poco f6"],
                "s": {
                    "general": 205, "red_dot": 165, "scope_2x": 170, "scope_4x": 190,
                    "awm": 95, "freelook": 60, "button": 47, "dpi": 720,
                },
            },
        ],
        "default": {
            "general": 196, "red_dot": 156, "scope_2x": 161, "scope_4x": 180,
            "awm": 88, "freelook": 55, "button": 50, "dpi": 668,
        },
    },
    "iphone": {
        "brands": ["iphone", "айфон", "apple", "эпл", "ios"],
        "presets": [
            {
                "match": ["iphone 6", "iphone 7", "iphone 8", "iphone se", "6s", "7s", "8 plus", "se 2", "se 3"],
                "s": {
                    "general": 178, "red_dot": 140, "scope_2x": 145, "scope_4x": 165,
                    "awm": 76, "freelook": 44, "button": 55, "dpi": 600,
                },
            },
            {
                "match": [
                    "iphone x", "iphone xs", "iphone xr", "iphone 11", "iphone 12",
                    "11 pro", "12 pro", "12 mini",
                ],
                "s": {
                    "general": 188, "red_dot": 150, "scope_2x": 155, "scope_4x": 174,
                    "awm": 84, "freelook": 52, "button": 51, "dpi": 645,
                },
            },
            {
                "match": [
                    "iphone 13", "iphone 14", "iphone 15", "iphone 16",
                    "13 pro", "14 pro", "15 pro", "16 pro", "13 mini", "14 plus", "15 plus",
                ],
                "s": {
                    "general": 197, "red_dot": 157, "scope_2x": 162, "scope_4x": 181,
                    "awm": 89, "freelook": 56, "button": 50, "dpi": 672,
                },
            },
        ],
        "default": {
            "general": 188, "red_dot": 150, "scope_2x": 155, "scope_4x": 174,
            "awm": 84, "freelook": 52, "button": 51, "dpi": 645,
        },
    },
    "huawei": {
        "brands": ["huawei", "хуавей", "honor", "хонор"],
        "presets": [
            {
                "match": [
                    "p20", "p30", "p40", "p50", "p60",
                    "mate 20", "mate 30", "mate 40", "mate 50", "mate 60", "p pro", "p lite",
                ],
                "s": {
                    "general": 193, "red_dot": 153, "scope_2x": 158, "scope_4x": 177,
                    "awm": 86, "freelook": 53, "button": 51, "dpi": 658,
                },
            },
            {
                "match": [
                    "honor x", "honor 70", "honor 80", "honor 90", "honor 100",
                    "x6", "x7", "x8", "x9", "x50",
                ],
                "s": {
                    "general": 187, "red_dot": 149, "scope_2x": 153, "scope_4x": 173,
                    "awm": 83, "freelook": 50, "button": 52, "dpi": 638,
                },
            },
        ],
        "default": {
            "general": 190, "red_dot": 151, "scope_2x": 156, "scope_4x": 175,
            "awm": 84, "freelook": 51, "button": 52, "dpi": 648,
        },
    },
    "oppo": {
        "brands": ["oppo", "оппо", "realme", "реалми", "vivo", "виво", "oneplus", "ванплас", "one plus"],
        "presets": [],
        "default": {
            "general": 186, "red_dot": 148, "scope_2x": 152, "scope_4x": 172,
            "awm": 82, "freelook": 50, "button": 52, "dpi": 636,
        },
    },
    "unknown": {
        "brands": [],
        "default": {
            "general": 185, "red_dot": 147, "scope_2x": 151, "scope_4x": 170,
            "awm": 81, "freelook": 49, "button": 53, "dpi": 628,
        },
    },
}

# ✅ ГОТОВО: handlers/ff_free_settings_data.py
