//-----------------------------------------------------------------------------
// name: chump_doc.cpp
// desc: chump page documentation generator for packages
//
// author: Nick Shaheed (nshaheed@ccrma.stanford.edu)
//         Ge Wang (ge@ccrma.stanford.edu)
// date: Spring 2025
//-----------------------------------------------------------------------------
#include "package.h"
#include "package_directory.h"
#include "package_list.h"

#include <iostream>
#include <sstream>
#include <string>

// c++ namespace setup
namespace fs = std::filesystem;
using std::optional;
using std::string;
// blunt instrument
using namespace std;


// function prototypes
string generate_mainIndex_MD_html( PackageList p );
string generate_mainIndex_MD( PackageList p );
string generate_page_MD_html( Package p );
string generate_page_MD( Package p );


// string generate_page_HTML( Package p );
// string generate_mainIndex_HTML( PackageList p );




//-----------------------------------------------------------------------------
// name: main()
// desc: entry point
//-----------------------------------------------------------------------------
int main( int argc, const char** argv )
{
    // check arguments
    if( argc != 3 ) {
        std::cerr << "chump_doc [packages dir] [output dir]" << std::endl;
        return -1;
    }

    // packages dir
    fs::path packages_path = argv[1];
    fs::path packages_subdir = packages_path / "packages";
    // output dir
    fs::path output_dir = argv[2];

    // check packages subdir
    if( !fs::exists( packages_subdir ) || !fs::is_directory( packages_subdir ) ) {
        std::cout << "no 'packages' dir found in " << packages_path
            << " make sure you pointed to the chump-packages repo correctly"
            << std::endl;
        return -1;
    }

    // check output dir
    if( !fs::exists( output_dir ) ) {
        std::cout << "output dir '" << output_dir << "' not found" << std::endl;
        return -1;
    }

    // a vector packages
    std::vector<Package> packages;

    // iterate over contents of packages subdir
    for( auto const & path : fs::directory_iterator{ packages_subdir } )
    {
        // if not a directory, move on to next entry
        if( !fs::is_directory( path ) )
            continue;

        // NOTE: each directory corresponds to a package

        // grab the package.json
        fs::path pkg_path = path.path() / "package.json";
        // std::cout << pkg_path << std::endl;

        // check package.json file
        if( !fs::exists( pkg_path ) ) {
            std::cerr
                << "package definition '" << pkg_path
                << "' not found; are you in the chump-packages/packages directory?"
                << std::endl;
            continue;
        }

        // read package from package.json
        Package pkg = read_package( pkg_path );
        // populate versions of package
        populate_versions( &pkg, path );
        // add to vector of packages
        packages.push_back( pkg );
    }

    // a package list
    PackageList package_list( packages );
    // create output dir packages directory
    // fs::create_directory( output_dir / "packages" );

    // iterate over package list
    for( auto const & p : package_list.get_packages() )
    {
        // skip over these!
        if( p.name == "TestPackage" || p.name == "TestPackageDir" ) continue;

        // the path
        fs::path pkg_dir = output_dir / p.name;
        // if not exist, create directory
        if( !fs::exists( pkg_dir ) ) fs::create_directory( pkg_dir );

        // the package info "chump page" (html portion)
        fs::path filename = "index.html";
        // path to the chump page
        fs::path pkg_path = pkg_dir / filename;
        // open the file
        std::ofstream out( pkg_path );
        // generate the chump page for the package
        out << generate_page_MD_html( p );
        // close the file
        out.close();

        // the package info "chump page" (md portion)
        filename = "index.md";
        // path to the chump page
        pkg_path = pkg_dir / filename;
        // open the file
        std::ofstream out_md( pkg_path );
        // generate the chump page for the package
        out_md << generate_page_MD( p );
        // close the file
        out_md.close();
    }

    // main index.html
    fs::path path_html = output_dir / "index.html";
    // open the file
    std::ofstream out_html( path_html );
    // output the package
    out_html << generate_mainIndex_MD_html( package_list );
    // close the file
    out_html.close();

    // main index.md
    fs::path path_md = output_dir / "index.md";
    // open the file
    std::ofstream out_md( path_md );
    // output the package
    out_md << generate_mainIndex_MD( package_list );
    // close the file
    out_md.close();
}




//-----------------------------------------------------------------------------
// name: generate_page_MD_html()
// desc: generate Markdown chump page index.html
//-----------------------------------------------------------------------------
string generate_page_MD_html( Package p )
{
    // string stream
    std::stringstream ss;

    ss << R"(<!DOCTYPE html>
<html lang="en">

  <head>
    <script type="module" src="https://cdn.jsdelivr.net/gh/zerodevx/zero-md@2/dist/zero-md.min.js"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/purecss@2.0.6/build/pure-min.css" integrity="sha384-Uu6IeWbM+gzNVXJcM9XV3SohHtmWE+3VGi496jvgX1jyvDTXfdK+rfZc8C1Aehk5" crossorigin="anonymous">
    <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">

    <!-- character set -->
    <meta charset="utf-8">

    <!-- meta properties -->
    <meta name="author" content="ChucK Team">
    <meta name="description" content="Downloadable ChucK Packages, available via ChuMP">
    <meta property="og:type" content="website" />
    <meta property="fb:app_id" content="966242223397117" /> <!--default app id-->
    <meta property="og:image" content="http://chuck.stanford.edu/doc/images/downchuck-logo2025w.png" />
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="manifest" href="/site.webmanifest">)";

    // TODO: get keywords as a vector, and append to list
    ss << "<meta name=\"keywords\" content=\"" << "chuck, package, chump, "/* + keywords */ << "\">" << endl;
    ss << "<meta property=\"og:title\" content=\"" << p.name << "\">" << endl;
    ss << "<meta property=\"og:description\" content=\"" << p.description << "\">" << endl;
    ss << "<meta property=\"og:url\" content=\"http://chuck.stanford.edu/release/chump/" + p.name + "/\">" << endl;
    ss << "<link rel=\"canonical\" href=\"http://chuck.stanford.edu/release/chump/" + p.name + "/\">" << endl;

    ss << "<!-- title -->" << endl;
    ss << "<title>" << p.name + " | ChucK Package" << "</title>" << endl;

    ss << R"(
  </head>

  <body>
    <div class="pure-g">
      <div class="w3-container w3-content w3-left-align w3-padding-64" style="max-width:1000px" id="band">
        <div class="pure-u-1-1 center">
          <zero-md src="./index.md"></zero-md>
        </div>
      </div>
    </div>
    
  </body>
</html>
)";

    // return stream as string
    return ss.str();
}




//-----------------------------------------------------------------------------
// name: generate_page_MD()
// desc: generate Markdown chump page index.md
//-----------------------------------------------------------------------------
string generate_page_MD( Package p )
{
    // string stream
    std::stringstream ss;

    ss << R"(<div align="center"><img src="../../../doc/images/downchuck-logo2025c.png" width="25%"></img>
<h2><a href="../">ChucK Package</a></h2>
(require <a target="_blank" href="../../">chuck 1.5.5.0 or higher</a>)
</div>

)";
    ss << "# **" << p.name << "**" << endl;
    ss << p.description << endl;
    ss << endl;

    ss << "*To install this package, type in terminal:*" << endl;
    ss << "```txt" << endl;
    ss << "  chump install " << p.name << endl;
    ss << "```" << endl;
    ss << endl;

    // homepage
    if( p.homepage != "" )
    {
        ss << "### Homepage" << endl;
        ss << "[**" << p.homepage << "**](" << p.homepage << ")" << endl;
    }

    // repo
    if( p.repository != "" )
    {
        ss << "### Source Repository" << endl;
        ss << "[**" << p.repository << "**](" << p.repository << ")" << endl;
    }

    ss << "### License" << endl;
    ss << p.license << endl;

    ss << "### Latest Versions" << endl;

    optional<PackageVersion> linux = p.latest_version( "linux" );
    optional<PackageVersion> win = p.latest_version( "windows" );
    optional<PackageVersion> mac = p.latest_version( "mac" );

    ss << "* macOS: " << (mac ? mac.value().getVersionString() : "[not available]") << endl;
    ss << "* Linux: " << (linux ? linux.value().getVersionString() : "[not available]") << endl;
    ss << "* Windows: " << (win ? win.value().getVersionString() : "[not available]") << endl;

    ss << "### File Browser" << endl;
    ss << "Manually [browse versions and packages files](./files) on server." << endl;
    ss << endl;

    // return stream as string
    return ss.str();
}




//-----------------------------------------------------------------------------
// name: generate_mainIndex_MD()
// desc: generate main packages index.html for Markdown
//-----------------------------------------------------------------------------
string generate_mainIndex_MD_html( PackageList pkg_list )
{
    // string stream
    std::stringstream ss;

    ss << R"(<!DOCTYPE html>
<html lang="en">

  <head>
    <script type="module" src="https://cdn.jsdelivr.net/gh/zerodevx/zero-md@2/dist/zero-md.min.js"></script>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/purecss@2.0.6/build/pure-min.css" integrity="sha384-Uu6IeWbM+gzNVXJcM9XV3SohHtmWE+3VGi496jvgX1jyvDTXfdK+rfZc8C1Aehk5" crossorigin="anonymous">
    <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">

    <!-- character set -->
    <meta charset="utf-8">

    <!-- meta properties -->
    <meta name="author" content="ChucK Team">
    <meta property="og:type" content="website" />
    <meta property="fb:app_id" content="966242223397117" /> <!--default app id-->
    <meta property="og:image" content="http://chuck.stanford.edu/doc/images/downchuck-logo2025w.png" />
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="manifest" href="/site.webmanifest">

    <meta name="keywords" content="chuck, packages, chump, computer music">
    <meta property="og:title" content="Downloadable ChucK Packages" />
    <meta property="og:description" content="Downloadable ChucK Packages" />
    <meta property="og:url" content="http://chuck.stanford.edu/release/chump/" />
    <link rel="canonical" href="http://chuck.stanford.edu/release/chump/" />

    <!-- title -->
    <title>ChucK Packages</title>
    <meta name="description" content="Downloadable ChucK Packages, available via ChuMP">
  </head>

  <body>
    
    <div class="pure-g">
      <div class="w3-container w3-content w3-left-align w3-padding-64" style="max-width:1000px" id="band">
        <div class="pure-u-1-1 center">
          <zero-md src="./index.md"></zero-md>
        </div>
      </div>
    </div>
    
  </body>
</html>
)";

    // return stream as string
    return ss.str();

}




//-----------------------------------------------------------------------------
// name: generate_mainIndex_MD()
// desc: generate main packages index.md for Markdown
//-----------------------------------------------------------------------------
string generate_mainIndex_MD( PackageList pkg_list )
{
    // string stream
    std::stringstream ss;

    ss << R"(<img src="../../doc/images/downchuck-logo2025c.png" width="35%"></img>
# Downloadable ChucK Packages

This is a listing of all available packages that can be downloaded and installed using  [**ChuMP**](../../chump/)—ChucK's (all-new) package manager for macOS, Linux, and Windows. As of ChucK `1.5.5.0`, ChuMP is bundled with the [ChucK release](../) on macOS and Windows (Linux users can [build from source](../../chump/linux-build.html)). Many more packages are on the way, from both the ChucK community and ChucK Team. Please visit the [ChuMP site](../../chump/) for more information on using and contributing to ChuMP.

BTW it is also possible to browse packages using ChuMP in terminal:

```txt
  chump list
```
To list packages currently installed on your computer:
```text
  chump list -i
```

# Available Packages)" << std::endl << std::endl;

    // get packages
    vector<Package> packages = pkg_list.get_packages();
    // sort
    std::sort(packages.begin(), packages.end());

    // iterate over packages
    for( auto & p : packages )
    {
        // skip over these!
        if( p.name == "TestPackage" || p.name == "TestPackageDir" ) continue;

        // optional<PackageVersion> mac = p.latest_version( "mac" );
        // string version = (mac ? " (" + mac.value().getVersionString() + ")" : "");
        string version = ""; // empty for now
        ss << "* [**" << p.name << "**](./" << p.name << "/)" << version << ": " << p.description << std::endl;
    }

    // return stream as string
    return ss.str();
}




//-----------------------------------------------------------------------------
// name: generate_HTML()
// desc: generate HTML chump page
//-----------------------------------------------------------------------------
string generate_page_HTML( Package p )
{
    std::stringstream ss;

    ss << "<html>";
    ss << "<title>" << p.name << "</title>";
    ss << "<body>";

    ss << "<h1>" << p.name << "</h1>";

    ss << "<p> install command: chump install " << p.name << "</p>";

    // ss << "<p> authors: " << p.

    ss << "<p>" << p.description << "</p>";

    ss << "<p> Homepage: "
        << "<a href=\"" << p.homepage << "\">" << p.homepage << "</a>"
        << "</p>";
    ;
    ss << "<p> Repository: "
        << "<a href=\"" << p.repository << "\">" << p.repository << "</a>"
        << "</p>";

    ss << "<p> License: " << p.license << "</p>";

    // Current versions (mac, windows, linux)
    ss << "<p>"
        << "Current versions:"
        << "</p>";

    optional<PackageVersion> linux = p.latest_version( "linux" );
    optional<PackageVersion> win = p.latest_version( "windows" );
    optional<PackageVersion> mac = p.latest_version( "mac" );

    ss << "<table>";
    if( linux )
        ss << "<tr>"
        << "<th>"
        << "linux"
        << "</th>"
        << "<th>" << linux.value().getVersionString() << "</th>"
        << "</tr>";
    if( win )
        ss << "<tr>"
        << "<th>"
        << "windows"
        << "</th>"
        << "<th>" << win.value().getVersionString() << "</th>"
        << "</tr>";
    if( mac )
        ss << "<tr>"
        << "<th>"
        << "mac"
        << "</th>"
        << "<th>" << mac.value().getVersionString() << "</th>"
        << "</tr>";
    ss << "</table>";

    ss << "</body>";
    ss << "</html>";

    return ss.str();
}




//-----------------------------------------------------------------------------
// name: generate_mainIndex_HTML()
// desc: generate main packages index in HTML
//-----------------------------------------------------------------------------
string generate_mainIndex_HTML( PackageList pkg_list )
{
    std::stringstream ss;

    ss << "<html>";
    ss << "<title>"
        << "ChuMP"
        << "</title>";
    ss << "<body>";

    ss << "<h1>"
        << "ChuMP (the ChucK Manager of Packages)"
        << "</h1>";
    ss << "<h2>"
        << "Package Directory"
        << "</h2>";

    ss << "<table>";
    for( auto const& p : pkg_list.get_packages() ) {
        ss << "<tr>"
            << "<th>"
            << "<a href=\"./packages/" << p.name << ".html\">" << p.name << "</a>"
            << "</th>"
            << "<th>" << p.description << "</th>"
            << "</tr>";
    }
    ss << "</table>";

    return ss.str();
}
