from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotVisibleException
from selenium.webdriver.common.keys import Keys
import selenium
from browsermobproxy import Server

import time, code, re, errno, urllib2, os, argparse, sys

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

class logger(object):
    def __init__(self, logfile):
        self.logfile = logfile
        self.fd = open(self.logfile, "w")
    def cleanup(self):
        self.fd.close()
    def __enter__(self):
        return self
    def __exit__(self ,type, value, traceback):
        self.cleanup()
    def write(self,a):
        if type(a) in (type(''),type(u'')):
            print a
            self.fd.write(a)
            self.fd.write("\n")
        elif type(a) in (type({}),type([])):
            self.fd.write(str(a))
            self.fd.write("\n")
        else:
            self.fd.write(str(a))    
            self.fd.write("\n")
            for x in dir(a):
                self.write(x)
                try:
                    self.write( str(getattr(a,x)) )
                except: pass
        self.fd.flush()            

class NotLoggedInException(Exception):
    pass
class VideoNotFoundException(Exception):
    pass

class VipScraper(object):
    USERNAME = os.environ["VIPTV_USERNAME"]
    PASSWORD = os.environ["VIPTV_PASSWORD"]
    
    URI_BASE = "http://viptv.net"
    HOME_URL =  URI_BASE + "/index.php"
    LOGIN_URI = URI_BASE + "/login_s.php"
    SEARCH_URI = URI_BASE + "/search_list.php?keyword_main={}"
    PROFILE_URI = URI_BASE + "/profile.php"
    FREE_URI = URI_BASE + "/free.html"
    
    PROXY_BINARY = "/browsermob-proxy/browsermob-proxy-2.1.3/bin/browsermob-proxy"
    
    def __init__(self, load_profile=False, use_proxy=True):
        if use_proxy:
            self.server = Server(self.PROXY_BINARY)
            self.server.start()
            self.proxy = self.server.create_proxy()
            self.ffprofile  = webdriver.FirefoxProfile()
            self.ffprofile.set_proxy(self.proxy.webdriver_proxy())
            self.browser = webdriver.Firefox(firefox_profile=self.ffprofile)
        else:
            self.browser = webdriver.Firefox() # Get local session of firefox
            
        try:
            self.browser.set_page_load_timeout(45)
            self.Username = ""
            self.Points = ""
            while 1:
                try:
                    self.browser.get(self.FREE_URI)
                    self.logged_in = False
                    while not self.logged_in:
                        try:
                            to_login_button = self.browser.find_element_by_id("login_bar_a")
                            to_login_button.click()
                            _=self.wait_for_response(self.browser.find_elements_by_name,["login_in"],timeout=2)
                            self.logged_in = True
                        except EnvironmentError:
                            continue
                        except ElementNotVisibleException:
                            continue
                    
                    login_button = self.wait_for_response(self.browser.find_elements_by_name,["login_in"])
                    assert len(login_button) == 1
                    login_button, = login_button
                    
                    
                    login_user = self.browser.find_element_by_name("uname_signin") # Find the query box
                    login_password = self.browser.find_element_by_name("pword_signin") # Find the query box

                    login_user.send_keys(self.USERNAME)
                    login_password.send_keys(self.PASSWORD)
                    
                    login_title = self.browser.title
                    while login_title == self.browser.title:
                        login_button.click()
                        time.sleep(3)
                    
                    if load_profile:
                        self.profile()
                    break
                except TimeoutException:
                    continue
        except:
            self.cleanup()
            raise
        
    def search_by_title(self, search_term):
        # .find_elements_by_xpath("//*[contains(text(), 'My Button')]")
        while 1:
            try:
                self.browser.get(self.SEARCH_URI.format(search_term))
                return self.browser.find_element_by_id("tv_search1").find_elements_by_tag_name("a")
            except TimeoutException:
                continue
            
    def profile(self):
        self.browser.get(self.PROFILE_URI)
        
        msg = self.browser.find_element_by_class_name("warning").text
        
        uname_re = "Hi!\s+(\w+),"
        uname_search = re.search(uname_re, msg)
        assert uname_search, "Unable to match '{}' in '{}'".format(uname_re, msg) 
        assert uname_search.group(1).lower() == self.USERNAME.lower(), "Unknown login username {}".format(uname_search.group(1).lower())
        self.Username = uname_search.group(1)
        
        points_re = "You have ([0-9]+) Pts"
        points_search = re.search(points_re, msg)
        assert points_search, "Unable to match '{}' in '{}'".format(points_re, msg)
        self.Points = int(points_search.group(1),10)
        
    def show(self, title):
        possibles = self.search_by_title(title)
        assert len(possibles) == 1, "Unable to locate the exact request: '{}'".format(title)
        link, = possibles
        self.Title = link.text
        link.click()          
        
    def cleanup(self):
        self.server.stop()
        del self.server
        self.browser.close()
        self.browser.quit()
        del self.browser        

    def __enter__(self):
        return self
    def __exit__(self ,type, value, traceback):
        self.cleanup()

    def wait_for_response( self, call, args=[], timeout=10):
        if not type(args) == type([]):
            raise TypeError("Args needs to be a list")
        t =  time.time()
        while time.time() - t < timeout:
            try:
                # sys.stderr.write(*args)
                r = call(*args)
                assert r
                return r
            except AssertionError:
                pass
        raise EnvironmentError("Unable to receive response before timeout")
    
    def require_login(self):
        while 1:
            try:
                if self.browser.find_elements_by_xpath("//*[contains(text(), 'Please sign in to watch this video')]"):
                    AA = self.browser.find_elements_by_xpath("//*[contains(text(), 'Please sign in to watch this video')]")[0]
                    if AA.tag_name == 'div':
                        raise NotLoggedInException()
                break
            except TimeoutException:
                continue
        
class VipShow(VipScraper):
    def __init__(self, show_title, load_profile=False):
        self.Title = show_title
        VipScraper.__init__(self, load_profile=load_profile)
        self.show(self.Title)
        
    def seasons(self):
        self.show(self.Title)
        time.sleep(10)
        tries = 0
        while tries < 50:
            try:
                print "'{}' {}".format(self.Title, tries)
                div_box = [ x for x in self.wait_for_response(self.browser.find_elements_by_class_name,["row"]) if x.text.count("{} Season".format(self.Title)) > 1]
                assert len(div_box), "Unable to locate season list"
                break
            except AssertionError:
                tries += 1
                if tries < 50:
                    continue
                raise
        div_box.sort(key=lambda x: len(x.text))
        container = div_box[0]
        assert "Season 1" in container.text, "Unable to locate seasons list"
        
        Seasons = []
        for e in container.find_elements_by_tag_name("a"):
            Seasons.append( Season(self, e) )
        Seasons.sort(key=lambda x: x.Season)
        
        return Seasons

class Season():
    def __init__(self, scraper, obj):
        self.scraper = scraper
        self.Text = obj.text
        
        season_re = "Season ([0-9]+)"
        season_search = re.search(season_re, self.Text)
        assert season_search, "Unable to match '{}' in '{}'".format(season_re, self.Text)
        self.Season = int(season_search.group(1),10)
        
        self.Link = obj.get_attribute('href')
        print self.Text
        
    def episodes(self):
        self.scraper.browser.get(self.Link)
        time.sleep(10)
        div_box = [ x for x in self.scraper.wait_for_response(self.scraper.browser.find_elements_by_class_name,["row"]) if "E01" in x.text]
        assert len(div_box), "Unable to locate episodes list"
        div_box.sort(key=lambda x: len(x.text))
        container = div_box[0]
        assert "E01" in container.text, "Unable to locate episodes list"
        
        Episodes = []
        for e in container.find_elements_by_tag_name("a"):
            Episodes.append( Episode(self.scraper, e) )
            print e.text
        Episodes.sort(key=lambda x: (x.Show, x.Season, x.Episode))
        
        return Episodes
            
class Episode():
    def __init__(self, scraper, obj, destination='/data'):
        self.scraper = scraper
        self.Text = obj.text
        
        season_re = "S([0-9]+)E([0-9]+)\s(.*)"
        season_search = re.search(season_re, self.Text)
        assert season_search, "Unable to match '{}' in '{}'".format(season_re, self.Text)
        self.Season = int(season_search.group(1),10)
        self.Episode = int(season_search.group(2),10)
        self.Title = season_search.group(3)
        
        show_re = "(.*?) - VIPTV.NET"
        show_search = re.search(show_re, obj.parent.title)
        assert show_search, "Unable to match '{}' in '{}'".format(show_re, self.title)
        self.Show = show_search.group(1)
        
        self.Link = obj.get_attribute('href')
        
        self.destination = destination
        self.file_path, self.file_name = "{0}/{1}".format(self.Show, self.Season), u"S{:d}E{:d}_{}.mp4".format(self.Season, self.Episode, self.Title.replace(" ","-"))
        self.fname = os.path.join(self.destination,self.file_path,self.file_name)
        
    def get(self, download = False):
        while 1:
            try:
                self.scraper.browser.get(self.Link)
                break
            except TimeoutException:
                    continue
        self.scraper.require_login()
        
        if os.path.exists(self.fname):
            return self.Link
        
        self.scraper.proxy.new_har()
        while not "newipad.mp4" in str(self.scraper.proxy.har):
            movie_player = self.scraper.wait_for_response(self.scraper.browser.find_element_by_id,["myElement"])
            movie_player.click()
        for x in self.scraper.proxy.har['log']['entries']:
            if "newipad.mp4" in x['request']['url']:
                if download:
                    while 1:
                        try:
                            self.scraper.browser.get(self.scraper.PROFILE_URI)
                            break
                        except TimeoutException:
                            continue
                    self.download_video(x['request']['url'])
                return x['request']['url']
                
        raise VideoNotFoundException()
        
    def download_video(self, video_url):
        u = urllib2.urlopen(video_url)
        
        mkdir_p(os.path.join(self.destination,self.file_path))   
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        if os.path.exists(self.fname) and os.stat(self.fname).st_size == file_size:
            return
        f = open( self.fname, 'wb')
        print "Downloading: %s Bytes: %s" % (self.file_name, file_size)

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,

        f.close()
        
    def __str__(self):
        return "{} Season {:d}-{:d}:{}".format(self.Show, self.Season, self.Episode, self.Title)
    
if __name__ =='__main__':
    parser = argparse.ArgumentParser(description="Video downloader for VIPTV.NET")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-v", "--verbose", action="store_true")
    group.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("title", type=str, help="Show title to download")
    parser.add_argument("season", type=int, default=-1, help="Season to download from. -1 for most recent")
    parser.add_argument("episodes", type=int, nargs="+", default=-1, help="Episodes to download from. -1 for most recent")
    args = parser.parse_args()
    
    with VipShow(args.title, load_profile = True) as vs:
        if args.verbose:
            print vs.Username, 'has', vs.Points
        show_season = vs.seasons()
        _season = args.season - 1 if args.season > 0 else -1
        try:
            if args.verbose:
                print show_season[_season]
            E = show_season[_season].episodes()
            try:
                for e in args.episodes:
                    _e = e - 1 if e > 0 else -1
                    if args.verbose:
                        print E[_e]
                    E[_e].get(True)
                exit(0)
            except IndexError:
                if not args.quiet:
                    sys.stderr.write("Episode {} not found out of {} episodes.\n".format(e,len(E)))
                exit(1)
        except IndexError:
            if not args.quiet:
                sys.stderr.write("Season {} not found out of {} seasons.\n".format(_season,len(show_season)))
            exit(1)
    
    # with logger("/data/inspect") as l:
        # with VipShow("The Big Bang Theory", load_profile = True) as vs:
            # try:
                # for s in vs.seasons():
                    # E = s.episodes()
                    # E[0].get(True)
                    # E[1].get(True)
                    # E[2].get(True)
                # # print vs.Username, vs.Points
                # # g = vs.episodes()[0].get(True)
                # # l.write(g)
            # except Exception as e:
                # print type(e), e
                # raw_input("click to end")
                # raise
            # finally:
                # pass #raw_input('Press enter to end')