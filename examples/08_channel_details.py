"""Fetch detailed metadata for a single channel (by id, @handle or URL).

Run with:  python examples/08_channel_details.py
"""

from ytscrape import YouTube


def main() -> None:
    with YouTube() as yt:
        # A channel id, @handle or any channel URL all work.
        details = yt.channel("https://www.youtube.com/@CodeBrux")

        print(f"Title:        {details.title}")
        print(f"Handle:       {details.handle}")
        print(f"Subscribers:  {details.subscribers}")
        print(f"Videos:       {details.video_count}")
        print(f"Views:        {details.view_count}")
        print(f"Country:      {details.country}")
        print(f"Joined:       {details.joined_date}")
        print(f"Family safe:  {details.is_family_safe}")
        print(f"Photo:        {details.photo}")
        print(f"Banner:       {details.banner}")
        print(f"Keywords:     {', '.join(details.keywords[:5])}")
        print(f"URL:          {details.url}")
        print(f"Vanity URL:   {details.vanity_url}")
        print(f"RSS:          {details.rss_url}")
        if details.links:
            print(f"Links:        {details.links}")
        if details.description:
            print(f"Description:  {details.description[:120]}...")


if __name__ == "__main__":
    main()
