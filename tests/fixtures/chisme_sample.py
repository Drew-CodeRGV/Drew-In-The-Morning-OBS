"""Fictional capture rows for tests and the UI fixture. NOT real posts: every URL is a placeholder under a /sample- path."""
import datetime


def rows(now: datetime.datetime) -> list[dict]:
    def ago(h):
        return (now - datetime.timedelta(hours=h)).isoformat()
    return [
        # ---- should be KEPT
        {"platform": "Reddit", "source": "r/McAllen", "title": "Is anyone else seeing the line at the new Whataburger on 10th wrap around the block?", "text": "Drove by at 7 this morning and the drive-thru line was out into the street.",
         "url": "https://www.reddit.com/r/McAllen/comments/sample-1/", "posted": ago(5), "upvotes": 412, "comments": 133,
         "tldr": "Folks say the drive-thru line is spilling into the street at breakfast.", "riff": "Breakfast taquitos are a contact sport in the Valley, and the line is the warm-up."},
        {"platform": "Reddit", "source": "r/RGV", "title": "Why does the H-E-B on Expressway always have the best pan dulce at 6 AM?", "text": "Not complaining, just asking.", "url": "https://www.reddit.com/r/RGV/comments/sample-2/", "posted": ago(20),
         "upvotes": 250, "comments": 88, "riff": "Scientists are baffled. We are not asking questions, we are buying a dozen."},
        {"platform": "Facebook", "source": "Things To Do In The RGV (group)", "title": "Anybody know what the lights over Edinburg were last night?", "text": "Looked like a line of lights moving slow.", "url": "https://www.facebook.com/groups/sample/posts/3",
         "posted": ago(30), "reactions": 310, "comments": 140, "shares": 22, "tldr": "A group post asks about slow-moving lights in the Edinburg sky; commenters guess drones or a launch viewing party.", "riff": "Either aliens or the Starbase fans got a very long extension cord."},
        {"platform": "Facebook", "source": "Nomorecheezmeh", "title": "Road closure by the Pharr bridge has everybody asking for a detour", "text": "Closure is real, per the comments.", "url": "https://www.facebook.com/nomorecheezmeh/posts/sample-4",
         "posted": ago(8), "reactions": 120, "comments": 60, "confirmedBy": {"outlet": "KRGV", "url": "https://www.krgv.com/news/sample-closure"}, "tldr": "Commenters say the closure near the Pharr bridge is tying up traffic.", "riff": "GPS has entered the chat and left it just as fast."},
        {"platform": "Instagram", "source": "@rgv.eats", "title": "Valley sunrise over the palms this morning, no filter", "text": "", "url": "https://www.instagram.com/p/sample-5/", "posted": ago(3), "reactions": 900, "comments": 40},
        # ---- must be DROPPED
        {"platform": "Reddit", "source": "r/Brownsville", "title": "Teen arrested after fight outside a Brownsville high school", "text": "", "url": "https://www.reddit.com/r/Brownsville/comments/sample-6/", "posted": ago(6), "upvotes": 800, "comments": 300},
        {"platform": "Facebook", "source": "RGV.ME", "title": "Maria Gonzalez was caught cheating on her husband, call her at 956-555-0123", "text": "", "url": "https://www.facebook.com/RGV.ME/posts/sample-7", "posted": ago(4), "reactions": 700, "comments": 400},
        {"platform": "Reddit", "source": "r/Harlingen", "title": "Does anyone know the address of the guy with the loud truck, 1204 Pecan Street?", "text": "", "url": "https://www.reddit.com/r/Harlingen/comments/sample-8/", "posted": ago(9), "upvotes": 300, "comments": 120},
        {"platform": "Reddit", "source": "r/Edinburg", "title": "Local business owner is in debt and about to be evicted, my neighbor says", "text": "", "url": "https://www.reddit.com/r/Edinburg/comments/sample-9/", "posted": ago(11), "upvotes": 500, "comments": 99},
        {"platform": "Reddit", "source": "r/RGV", "title": "Old thread about the taco truck on Nolana", "text": "", "url": "https://www.reddit.com/r/RGV/comments/sample-10/", "posted": ago(200), "upvotes": 5000, "comments": 900},
        # ---- duplicate of a headline (dropped when headlines are passed)
        {"platform": "Reddit", "source": "r/RGV", "title": "Hidalgo County confirms its first New World screwworm case in a calf, quarantine covers 4 counties", "text": "", "url": "https://www.reddit.com/r/RGV/comments/sample-11/", "posted": ago(14), "upvotes": 600, "comments": 200},
    ]
