"""Genre detection module using Gemini with Google Search grounding."""

import os
from typing import Optional, List
from google import genai
from google.genai import types
from dataclasses import dataclass


@dataclass
class StationInfo:
    """Station information for genre detection."""

    call_sign: str
    frequency: float
    service_type: str
    city: str
    state: str


class GenreDetector:
    """Detects radio station genres using Gemini with Google Search grounding."""

    def __init__(self):
        """Initialize the genre detector with Gemini client."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        # Configure the client
        self.client = genai.Client(api_key=api_key)

        # Define the grounding tool
        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())

        # Track quota status for the API key
        self.quota_exceeded = False

    def detect_genre(self, station: StationInfo, max_retries: int = 3) -> Optional[str]:
        """
        Detect the genre of a radio station using Gemini with Google Search.

        Args:
            station: StationInfo object with station details
            max_retries: Maximum number of retries if grounding metadata is missing

        Returns:
            Detected genre as a string, or None if detection fails
        """
        # Check if quota is already exceeded for this API key
        if self.quota_exceeded:
            # Don't process any more stations - quota exceeded
            return None

        # Create a comprehensive search query
        query = self._build_genre_query(station)

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=query,
                    config=types.GenerateContentConfig(
                        tools=[self.grounding_tool],
                        temperature=0.3,  # Lower temperature for more consistent results
                    ),
                )

                # Check if response is properly grounded
                if not self._has_grounding_metadata(response):
                    print(
                        f"Attempt {attempt + 1}: No grounding metadata for {station.call_sign}, retrying..."
                    )
                    continue

                # Extract and clean the genre from response
                if response.text:
                    genre = self._extract_genre(response.text)
                    print(f"✓ {station.call_sign}: Successfully grounded response")
                    return genre
                return None

            except Exception as e:
                # Check if it's a quota/rate limit error
                error_msg = str(e).lower()
                if "quota" in error_msg or "exhausted" in error_msg or "429" in str(e):
                    print(f"🚫 Google Search Grounding quota exceeded for API key: {e}")
                    print(
                        "Daily limit of 500 grounding requests reached. Quota resets at midnight Pacific time."
                    )
                    print("All subsequent requests will be skipped until quota resets.")
                    self.quota_exceeded = (
                        True  # Mark quota as exceeded for this session
                    )
                    return None  # DO NOT write status to database - leave genre field empty
                print(f"Error detecting genre for {station.call_sign}: {e}")
                return None

        print(
            f"⚠ {station.call_sign}: Failed to get grounded response after {max_retries} attempts"
        )
        return None

    def detect_genres_batch(
        self, stations: List[StationInfo]
    ) -> dict[str, Optional[str]]:
        """
        Detect genres for multiple stations.

        Args:
            stations: List of StationInfo objects

        Returns:
            Dictionary mapping call_sign to detected genre
        """
        results = {}
        for station in stations:
            genre = self.detect_genre(station)
            results[station.call_sign] = genre
        return results

    def _build_genre_query(self, station: StationInfo) -> str:
        """Build a comprehensive query for genre detection."""
        freq_str = (
            f"{station.frequency:.1f} MHz"
            if station.service_type == "FM"
            else f"{station.frequency:.0f} kHz"
        )

        query = f"""
        What is the music genre or format of radio station {station.call_sign} {freq_str} in {station.city}, {station.state}?

        Please search for current information about this radio station and determine its primary music genre or format.
        Common radio formats include: Top 40/Pop, Rock, Country, Hip-Hop/R&B, Adult Contemporary, Classical, Jazz, News/Talk, Sports, Alternative Rock, Oldies, etc.

        Respond with just the primary genre/format in a few words (e.g., "Classic Rock", "Country", "News/Talk", "Top 40").
        If you cannot determine the genre, respond with "Unknown".
        """

        return query.strip()

    def _extract_genre(self, response_text: str) -> Optional[str]:
        """Extract and normalize the genre from the response."""
        if not response_text:
            return None

        # Clean up the response
        genre = response_text.strip()

        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            "The genre is",
            "The format is",
            "This station plays",
            "Primary genre:",
            "Format:",
            "Genre:",
        ]

        for prefix in prefixes_to_remove:
            if genre.lower().startswith(prefix.lower()):
                genre = genre[len(prefix) :].strip()

        # Remove quotes and extra punctuation
        genre = genre.strip(".\"'")

        # Normalize "Unknown" responses
        if any(
            word in genre.lower()
            for word in ["unknown", "unclear", "cannot determine", "not found"]
        ):
            return "Unknown"

        # Limit length and capitalize properly
        if len(genre) > 50:
            genre = genre[:50].strip()

        return genre if genre else None

    def _has_grounding_metadata(self, response) -> bool:
        """
        Check if the response contains grounding metadata.

        Args:
            response: The response object from Gemini API

        Returns:
            True if grounding metadata is present, False otherwise
        """
        try:
            if not hasattr(response, "candidates") or not response.candidates:
                return False

            candidate = response.candidates[0]

            # Check for grounding_metadata attribute (snake_case)
            if (
                hasattr(candidate, "grounding_metadata")
                and candidate.grounding_metadata
            ):
                metadata = candidate.grounding_metadata

                # Verify it has the essential grounding components
                has_chunks = (
                    hasattr(metadata, "grounding_chunks")
                    and metadata.grounding_chunks
                    and len(metadata.grounding_chunks) > 0
                )

                has_queries = (
                    hasattr(metadata, "web_search_queries")
                    and metadata.web_search_queries
                    and len(metadata.web_search_queries) > 0
                )

                return has_chunks and has_queries

            # Check for groundingMetadata attribute (camelCase) as fallback
            if hasattr(candidate, "groundingMetadata") and candidate.groundingMetadata:
                metadata = candidate.groundingMetadata

                # Verify it has the essential grounding components
                has_chunks = (
                    hasattr(metadata, "groundingChunks")
                    and metadata.groundingChunks
                    and len(metadata.groundingChunks) > 0
                )

                has_queries = (
                    hasattr(metadata, "webSearchQueries")
                    and metadata.webSearchQueries
                    and len(metadata.webSearchQueries) > 0
                )

                return has_chunks and has_queries

            return False

        except Exception as e:
            print(f"Error checking grounding metadata: {e}")
            return False


def get_genre_detector() -> GenreDetector:
    """Factory function to create a GenreDetector instance."""
    return GenreDetector()
