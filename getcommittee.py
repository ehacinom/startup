from bs4 import BeautifulSoup
import csv
import lxml
import re
from utils import *
import xmltodict
from collections import defaultdict

class GetCommittee(object):
    """
    Get data from website and move it to CSV
    Outputs 12 fields to 'committees.csv'
    Outputs committee names to 'committee_list.txt'
    
    
    Example
    
    from getcommittee import GetCommittee
    GetCommittee()
    
    """
    
    def __init__(self):
        """
        Get all data for committees
        
        SAVE TO FILE committees.csv
        data
            [CommitteeName, CommitteeType, Link, 
             Header, Chair, CoChair, 
             ViceChair, CommitteeClerk, LegislativeCouncilStaff, 
             Member, Other, Hearings,
             ComTopics]
    
        SAVE TO FILE committee_list.txt
        names of all the committees
    
        TODO
        Follow more links? Get more research? as I've skipped links for ease.
        Fix up edit_committee_info, it's long and repetitive.
    
        """
    
        root = 'http://docs.legis.wisconsin.gov/feed/2015/committees/'
        committee_type = ['Senate', 'Assembly', 'Joint', 'Other']
        self.topics = self.get_topics()
    
        data = []
        for ct in committee_type:
            # metadata
            # [committee name, committee_type, link]
            text = load_txt(root+ct)
            metadata = self.get_committee_metadata(text, ct)
        
            # other data
            infodata = self.get_committee_info(metadata)
            
            # write
            data.extend(infodata)
        
        # save list of committees to file
        with open('committee_list.txt', 'w') as f:
            for d in data:
                f.write(d[0] + '\n')
    
        # write list of lists to outfile
        header = ['CommitteeName', 'CommitteeType', 'Link', 
                  'Header', 'Chair', 'CoChair', 
                  'ViceChair', 'CommitteeClerk', 'LegislativeCouncilStaff', 
                  'Member', 'Other', 'Hearings', 'ComTopics']
        with open('committees.csv', 'w') as f:
            #quotechar="'", escapechar = '\\', lineterminator = '\r\n'
            # also see utils.py rm_unicode()
            writer = csv.writer(f, delimiter='|', quoting = csv.QUOTE_NONE)
            writer.writerow(header)
            writer.writerows(data)
    
        return None

    def edit_Joint_Committee(self, item):
        """
        Dealing with Joint Committee reports
        (esp from the Joint Legislative Audit Committee)
    
        In the future, check that the information skipped is reasonable
    
        INPUT
        item, the list of OrderedDicts with metadata on each committee
        Parameters and example data:
            (u'guid', OrderedDict([(u'@isPermaLink', u'false'), 
                                   ('#text', u'5b7a05a6-...')]))
            (u'link', u'http://docs.legis.wisconsin.gov/2015/committees')
            (u'title', u'Committee Name - 2016-12-17')
            (u'description', u'Committee Name')
            (u'pubDate', u'Sat, 17 Dec 2016 07:35:58 -0600')
            (u'a10:updated', u'2016-12-17T07:35:58-06:00')
    
        OUTPUT
        boolean, if data will be used
    
        """
    
        OtherJointCommitteeCrap = 'records'
        AnnoyingJointCommittees = ['Presentation', 'Report', 'Proceedings', 
                                   'Minutes', 'Proposed', 'Audio', 'Agenda']
    
        name = item['description']
        title = item['title']

        if not name: 
            return False
    
        if OtherJointCommitteeCrap in name:
            return False
    
        for ajc in AnnoyingJointCommittees:
            if ajc in title:
                return False
    
        return True
    
    def get_committee_metadata(self, text, committee_type):
        """
        Get metadata for committees
    
        INPUT
        text from load_txt(url)
        committee_type
    
        INTERMEDIARIES
        x is a list of items/OrderedDicts with metadata on each committee
        Parameters and example data:
            (u'guid', OrderedDict([(u'@isPermaLink', u'false'), 
                                   ('#text', u'5b7a05a6-...')]))
            (u'link', u'http://docs.legis.wisconsin.gov/2015/committees')
            (u'title', u'Committee Name - 2016-12-17')
            (u'description', u'Committee Name')
            (u'pubDate', u'Sat, 17 Dec 2016 07:35:58 -0600')
            (u'a10:updated', u'2016-12-17T07:35:58-06:00')
        
        OUTPUT
        data, [CommitteeName, CommitteeType, Link]
    
        """
    
        # x is a list of OrderedDict
        # should do some error catching here
        # find format of data through testing / pretty xml
        x = xmltodict.parse(text)['rss']['channel']['item']
    
        # iterate for relevant information
        data = []
        for item in x:
            name = item['description']
        
            interest = True
            if not name: 
                interest = False
        
            # dealing with Joint Committee reports
            if committee_type == 'Joint':
                interest = self.edit_Joint_Committee(item)
        
            # add to data
            if interest:
                data.append([name, committee_type, item['link']])
    
        return data
    
    def get_topics(self):
        """Get committees and hand-assigned topics."""
        topics = defaultdict(str)
        with open('committee_topics.txt', 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                topics[row[0]] = row[1]
        
        return topics
    
    def edit_committee_info(self, info):
        """
        String editing to get committee info
        Reduce text data from each parsed committee site
    
        INPUT
        info, text from get_committee_metadata()
    
        OUTPUT
        data, extrated from info
            [Header, Chair, CoChair, 
             ViceChair, CommitteeClerk, LegislativeCouncilStaff, 
             Member, Other, Hearings]
    
        TO DO
        Look into exceptions for names when adding spaces before capital letters 
        This info doesn't include Hearing Documents/In/Out/All/Proposals
        Can also clean this up a lot
            duplicates for committee members
        And instead of testing if len(a) == 2, check if a[0 or 1] == None
    
        """
        
        # name exceptions?
        names = ['VanderMeer', 'Bowers2']
    
        # rm header
        a = info.split('Notify', 1)[-1].lstrip().rstrip()
    
        # add space before every CAP preceded by ')' or '[a-z]' or '2' but NOT '\n', ' ' or '-'
        #b = re.sub(r'([a-z][a-z|\)])([A-Z])', r'\1\n\2', a)
        # first expression failed to exclude Rep. VanderMeer
        # https://regex101.com/r/XS0OC5/1
        b = re.sub(r'(?!VanderM)([A-Z|\(]\w+[a-z|\)|2])([A-Z])', r'\1\n\2', a)
    
        # add space before '(' - rare
        # eg for clerk phone number
        c = re.sub(r'([a-z])\(', r'\1 (', b)
        
        # replace '\r\n ' to '\n'
        d = re.sub(r'\r\n +', '\n', c)
    
        # lots of spaces to one
        e = re.sub(' +', ' ', d)
    
        # split off hearings
        hearings = None
        f = e.split('Hearing Notices')
        if len(f) == 1: f = f[0]
        elif len(f) == 2:
            f, hearings = f
        
            # parse
            hearings = re.sub('Executive Session ', 'Private', hearings)
            hearings = re.sub('Public Session ', 'Public', hearings)
            hearings = hearings.lstrip().split('\n\n\n\n')
            tmp = []
            for h in hearings:
                h = re.sub('\n', '-', h)
                tmp.append(h)
        
            hearings = tmp
            
        else:
            w = 'get_data.edit_committee_info() split info into 3+ parts.'
            warning(w, info)
    
        # split into headers/chairs/staff/etc, _, members
        g, _, members = f.split('Members')
    
        # split into header/persons
        header, persons = [None] * 2
        h = filter(None, g.lstrip().rstrip().split('\n\n'))
        if h:
            persons = h.pop()
            if h:
                header = ' '.join([i.lstrip() for i in h])
    
        # setup
        Chair, CoChair, ViceChair = [], [], []
        CommitteeClerk, LegislativeCouncilStaff = [], []
        Member, Other = [], []
    
        # split persons 
        prev = None
        if persons:
            lines = persons.split('\n')
            for i, line in enumerate(lines):
                if not line: continue
            
                # Chair
                a = line.split(' (Chair)')
                if len(a) == 2:
                    Chair.append(a[0])
                    prev = Chair
                    continue
            
                # CoChair
                a = line.split(' (Co-Chair)')
                if len(a) == 2:
                    CoChair.append(a[0])
                    prev = CoChair
                    continue
                
                # ViceChair
                a = line.split(' (Vice-Chair)')
                if len(a) == 2:
                    ViceChair.append(a[0])
                    prev = ViceChair
                    continue
            
                # CommitteeClerk
                a = line.split('Committee Clerk ')
                if len(a) == 2:
                    CommitteeClerk.append(a[1])
                    prev = CommitteeClerk
                    continue
            
                # LegislativeCouncilStaff
                a = line.split('Legislative Council Staff ')
                if len(a) == 2:
                    LegislativeCouncilStaff.append(a[1])
                    prev = LegislativeCouncilStaff
                    continue
                
                # try/except to deal with missing committee pages from
                # turnover, jan 5 2017
                try:
                    # repeat name with no tag
                    prev.append(a[0].lstrip())
                except AttributeError:
                    warn = 'Missing committee chairs (new year), still added.'
                    warning(warn, lines)
                    Member.append(a[0].lstrip())
        
        # parse members
        lines = members.split('\n')
        for i, line in enumerate(lines):
            if not line: continue
        
            # Chair
            a = line.split(' (Chair)')
            if len(a) == 2:
                if a[0] in Chair: 
                    continue
                Chair.append(a[0])
                continue

            # CoChair
            a = line.split(' (Co-Chair)')
            if len(a) == 2:
                if a[0] in CoChair:
                    continue
                CoChair.append(a[0])
                continue

            # ViceChair
            a = line.split(' (Vice-Chair)')
            if len(a) == 2:
                if a[0] in ViceChair:
                    continue
                ViceChair.append(a[0])
                continue
        
            # Other
            if line.startswith(' '):
                Other.append(line.lstrip())
        
            # Member
            Member.append(line)
    
        # argh, some of these return data as just None 
        # so we're going to just set it to a None array
        # so it gets added
        data = [None for i in xrange(9)]
        
        
        # NOW THE SUPER JENKY PART HAPPENS
        # BECAUSE I DON'T WANT TO REWRITE
        # AND BECAUSE I DON'T WANT LISTS, I WANT STR
        # HERE GOES
        Chair = joiner(Chair)
        CoChair = joiner(CoChair)
        ViceChair = joiner(ViceChair)
        CommitteeClerk = joiner(CommitteeClerk)
        LegislativeCouncilStaff = joiner(LegislativeCouncilStaff)
        Member = joiner(Member)
        Other = joiner(Other)
        hearings = joiner(hearings)
        # WELP
        
        # return data
        data =  [header, Chair, CoChair, ViceChair, 
                 CommitteeClerk, LegislativeCouncilStaff, 
                 Member, Other, hearings]
        data = [d if d else None for d in data]
        return data
    
    def get_committee_info(self, metadata):
        """
        Follow links in committee metadata for individual committee info
    
        INPUT
        metadata from get_committee_metadata()
            list of str [name, committee_type, url]
    
        INTERMEDIARIES
        info is <class 'bs4.element.Tag'>
            Parsed HTML from <div class="span5">
                I think all the info that we would want is from this <div>
            Andy should check output
            Should we use the <html tags> for other links? 
                (Seems like a lot of work.)
        cominfo is from edit_committee_info()
            list of header, people+positions, hearing dates
    
        OUTPUT
        data
            [CommitteeName, CommitteeType, Link, 
             Header, Chair, CoChair, 
             ViceChair, CommitteeClerk, LegislativeCouncilStaff, 
             Member, Other, Hearings, ComTopics]
    
        """
    
        data = []
        for meta in metadata:
            # parse html
            name, committee_type, url = meta
            text = load_txt(url)
            parser = BeautifulSoup(text, "lxml")
            info = parser.body.find('div', attrs={'class':'span5'})
            
            # retrieve committee info
            if info:
                # remove unicode 
                info = rm_unicode(info.text)
                
                # [header, Chair, CoChair, ViceChair, CommitteeClerk, 
                #  LegislativeCouncilStaff, Member, Other, hearings]
                cominfo = self.edit_committee_info(info)
                
                # topics
                comtopics = self.topics[name]
                
                # don't add to data if missing cominfo
                tmp = meta + cominfo + list(comtopics)
                data.append(tmp)
            else:
                warn = 'Missing info in get_committee_info, still added.'
                warning(warn, meta)
                tmp = meta + [None for i in xrange(10)]
                data.append(tmp)
        
        return data
