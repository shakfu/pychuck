#--------------------------------------------------------------
# codesign.sh
# pre-condition: both arm64 and intel Chumpinate.chug builds
#  are located in the proper directories 
#--------------------------------------------------------------

# where the Chumpinate build can be found
CHUMPINATE_UB=./Chumpinate.chug

# remove code signature from chugin and dylibs
codesign --remove-signature ${CHUMPINATE_UB}

# codesign Chumpinate.chug
codesign --deep --force --verify --verbose --timestamp --options runtime --entitlements Chumpinate.entitlements --sign "Developer ID Application" ${CHUMPINATE_UB}
