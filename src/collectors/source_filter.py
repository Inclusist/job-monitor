"""
Job Source Filtering
Filters out jobs from low-quality, spammy, or unreliable sources
"""

from urllib.parse import urlparse
from typing import Dict, List, Optional


class SourceFilter:
    """Filters job sources based on quality and user preferences"""
    
    # Known low-quality job aggregators and spam sites
    BLACKLISTED_DOMAINS = {
        # Generic job aggregators (often outdated/spam)
        'learn4good.com',
        'jobilize.com',
        'job.fish',
        'bebee.com',
        'jooble.org',
        'trabajo.org',
        'jobsintheus.com',
        'whatjobs.com',
        'talentprise.com',
        'remote.co',
        'remotework.com',
        'globalwfh.lovestoblog',
        'remotenow.mysmartprosnetwfh',
        
        # Questionable quality boards
        'euroremotejobs.com',
        'workster.com',
        'dl-remote.com',
        'recooty.com',
        'jobgether.com',
        'jobtotaljobs.com',
        
        # Recruiter aggregators (often spam)
        'tomorrow-hire.com',
    }
    
    # High-quality, trusted sources
    WHITELIST_DOMAINS = {
        # Direct company career sites
        'careers.deliveryhero.com',
        'jobs.sasol.com',
        'pgcareers.com',
        
        # Major professional platforms
        'linkedin.com',
        'xing.com',
        'indeed.com',
        'glassdoor.com',
        'stepstone.de',
        'monster.de',
        'adzuna.de',
        
        # Quality German job boards
        'get-in-it.de',
        'jobware.de',
        'jobvector.de',
        'academics.de',
        
        # Tech-specific quality boards
        'stackoverflow.com',
        'github.com',
        'dice.com',
        'hired.com',
        'honeypot.io',
    }
    
    def __init__(self, user_blacklist: Optional[List[str]] = None):
        """
        Initialize source filter
        
        Args:
            user_blacklist: Additional domains to blacklist (optional)
        """
        self.user_blacklist = set(user_blacklist or [])
        
    def get_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return None
    
    def is_blacklisted(self, url: str) -> bool:
        """Check if URL's domain is blacklisted"""
        domain = self.get_domain(url)
        if not domain:
            return False
        
        # Check against default and user blacklists
        all_blacklisted = self.BLACKLISTED_DOMAINS | self.user_blacklist
        return domain in all_blacklisted
    
    def is_whitelisted(self, url: str) -> bool:
        """Check if URL's domain is whitelisted (trusted)"""
        domain = self.get_domain(url)
        if not domain:
            return False
        
        return domain in self.WHITELIST_DOMAINS
    
    def get_quality_score(self, url: str) -> int:
        """
        Get quality score for a job source
        
        Returns:
            3 = High quality (whitelisted)
            2 = Medium quality (neutral)
            1 = Low quality (blacklisted)
        """
        if self.is_whitelisted(url):
            return 3
        elif self.is_blacklisted(url):
            return 1
        else:
            return 2
    
    def should_filter(self, url: str, min_quality: int = 2) -> bool:
        """
        Determine if a job should be filtered out
        
        Args:
            url: Job URL to check
            min_quality: Minimum quality score required (1-3)
            
        Returns:
            True if job should be filtered out, False otherwise
        """
        quality = self.get_quality_score(url)
        return quality < min_quality
    
    def filter_jobs(self, jobs: List[Dict], min_quality: int = 2) -> List[Dict]:
        """
        Filter a list of jobs by source quality
        
        Args:
            jobs: List of job dictionaries with 'url' field
            min_quality: Minimum quality score (1=allow all, 2=remove blacklisted, 3=only whitelisted)
            
        Returns:
            Filtered list of jobs
        """
        filtered = []
        stats = {'total': len(jobs), 'filtered': 0, 'kept': 0}
        
        for job in jobs:
            url = job.get('url', '')
            if not self.should_filter(url, min_quality):
                filtered.append(job)
                stats['kept'] += 1
            else:
                stats['filtered'] += 1
                domain = self.get_domain(url)
                print(f"  Filtered out job from: {domain}")
        
        print(f"\nFiltering complete: {stats['kept']}/{stats['total']} jobs kept, {stats['filtered']} filtered")
        return filtered
    
    def get_domain_stats(self, jobs: List[Dict]) -> Dict[str, Dict]:
        """
        Get statistics about domains in job list
        
        Returns:
            Dict mapping domain -> {count, quality, is_blacklisted, is_whitelisted}
        """
        stats = {}
        
        for job in jobs:
            url = job.get('url', '')
            domain = self.get_domain(url)
            if not domain:
                continue
            
            if domain not in stats:
                stats[domain] = {
                    'count': 0,
                    'quality': self.get_quality_score(url),
                    'is_blacklisted': self.is_blacklisted(url),
                    'is_whitelisted': self.is_whitelisted(url),
                }
            
            stats[domain]['count'] += 1
        
        return stats


def test_filter():
    """Test the source filter"""
    filter = SourceFilter()
    
    test_urls = [
        'https://learn4good.com/job123',
        'https://de.linkedin.com/job456',
        'https://careers.google.com/job789',
        'https://jobilize.com/spam',
        'https://stackoverflow.com/jobs/12345',
    ]
    
    print("Testing SourceFilter:")
    print("=" * 60)
    
    for url in test_urls:
        domain = filter.get_domain(url)
        quality = filter.get_quality_score(url)
        blacklisted = filter.is_blacklisted(url)
        whitelisted = filter.is_whitelisted(url)
        should_filter_q2 = filter.should_filter(url, min_quality=2)
        
        print(f"\nURL: {url}")
        print(f"  Domain: {domain}")
        print(f"  Quality: {quality}/3")
        print(f"  Blacklisted: {blacklisted}")
        print(f"  Whitelisted: {whitelisted}")
        print(f"  Filter (min_q=2): {should_filter_q2}")


if __name__ == '__main__':
    test_filter()
