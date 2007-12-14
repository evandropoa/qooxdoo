#!/usr/bin/env python

################################################################################
#
#  qooxdoo - the new era of web development
#
#  http://qooxdoo.org
#
#  Copyright:
#    2006-2007 1&1 Internet AG, Germany, http://www.1and1.org
#
#  License:
#    LGPL: http://www.gnu.org/licenses/lgpl.html
#    EPL: http://www.eclipse.org/org/documents/epl-v10.php
#    See the LICENSE file in the project's top-level directory for details.
#
#  Authors:
#    * Sebastian Werner (wpbasti)
#
################################################################################

import re, os, sys, zlib

from modules import filetool
from modules import textutil

from generator2 import util
from generator2.ApiLoader import ApiLoader
from generator2.Cache import Cache
from generator2.DependencyLoader import DependencyLoader
from generator2.Locale import Locale
from generator2.PartBuilder import PartBuilder
from generator2.TreeLoader import TreeLoader
from generator2.TreeCompiler import TreeCompiler
from generator2.LibraryPath import LibraryPath


class Generator:
    def __init__(self, config, console, variants, settings, require, use):
        self._config = config
        self._console = console
        self._variants = variants
        self._settings = settings

        # Merge config deps and runtime deps
        require = self._mergeDicts(require, config.get("require", {}))
        use = self._mergeDicts(use, config.get("use", {}))

        # Scanning given library paths
        self.scanLibrary(config.split("library"))

        # Create tool chain instances
        self._cache = Cache(config.split("cache"), self._console)
        self._treeLoader = TreeLoader(self._classes, self._cache, self._console)
        self._depLoader = DependencyLoader(self._classes, self._cache, self._console, self._treeLoader, require, use)
        self._treeCompiler = TreeCompiler(self._classes, self._cache, self._console, self._treeLoader)
        self._locale = Locale(self._classes, self._cache, self._console, self._treeLoader)
        self._apiLoader = ApiLoader(self._classes, self._cache, self._console, self._treeLoader)
        self._partBuilder = PartBuilder(self._console, self._depLoader, self._treeCompiler)

        # Start job
        #self.run()


    def _mergeDicts(self, source1, source2):
        target = {}

        for key in source1:
            if not target.has_key(key):
                target[key] = []

            target[key].extend(source1[key])

        for key in source2:
            if not target.has_key(key):
                target[key] = []

            target[key].extend(source2[key])

        return target



    def scanLibrary(self, library):
        self._console.info("Scanning libraries...")
        self._console.indent()

        classes = {}
        translation = {}
        ns = []
        
        for segment in library.iter():
            entryDir = segment.get("path", ".")

            self._console.debug("Path: %s" % entryDir)
            self._console.indent()
            
            path = LibraryPath(segment, self._console)
            
            segNamespace = path.getNamespace()
            segClasses = path.getClasses()
            segTranslation = path.getTranslation()

            ns.append(segNamespace)
            classes.update(segClasses)
            translation[segNamespace] = segTranslation
            
            self._console.outdent()

        self._console.outdent()
        self._console.debug("Loaded %s libraries" % len(ns))
        self._console.debug("")
        
        self._classes = classes
        self._translation = translation
        self._namespaces = ns
        
        

    def run(self):
        # Preprocess include/exclude lists
        # This is only the parsing of the config values
        # We only need to call this once on each job
        smartInclude, explicitInclude = self.getIncludes()
        smartExclude, explicitExclude = self.getExcludes()

        # Processing all combinations of variants
        variantData = self.getVariants()
        variantSets = util.computeCombinations(variantData)

        # Iterate through variant sets
        for variantSetNum, variants in enumerate(variantSets):
            if len(variantSets) > 1:
                self._console.head("Processing variant set %s/%s" % (variantSetNum+1, len(variantSets)))

                # Debug variant combination
                self._console.debug("Switched variants:")
                self._console.indent()
                for key in variants:
                    if len(variantData[key]) > 1:
                        self._console.debug("%s = %s" % (key, variants[key]))
                self._console.outdent()


            # Resolving dependencies
            self._console.info("Resolving dependencies...")
            self._console.indent()
            classList = self._depLoader.getClassList(smartInclude, smartExclude, explicitInclude, explicitExclude, variants)
            self._console.outdent()


            # Cleanup Task
            self.runClean(classList)

            # API Data Task
            self.runApiData(classList)


            # Check for package configuration
            if self._config.get("packages"):
                # Reading configuration
                partsCfg = self._config.get("packages/parts", {})
                collapseCfg = self._config.get("packages/collapse", [])
                sizeCfg = self._config.get("packages/size", 0)
                bootPart = self._config.get("packages/init", "boot")

                # Automatically add boot part to collapse list
                if bootPart in partsCfg and not bootPart in collapseCfg:
                    collapseCfg.append(bootPart)

                # Expanding expressions
                self._console.debug("Expanding include expressions...")
                partIncludes = {}
                for partId in partsCfg:
                    partIncludes[partId] = self._expandRegExps(partsCfg[partId])

                # Computing packages
                partContent, packageContent = self._partBuilder.getPackages(partIncludes, smartExclude, classList, collapseCfg, variants, sizeCfg)

            else:
                # Emulate configuration
                bootPart = "boot"
                partContent = { "boot" : [0] }
                packageContent = [classList]


            # Locale Task
            self.runLocale(partContent, packageContent, variants)

            # Source Task
            self.runSource(partContent, packageContent, bootPart, variants)

            # Compiled Task
            self.runCompiled(partContent, packageContent, bootPart, variants)

            # Dependeny Debug Task
            self.runDependencyDebug(partContent, packageContent, variants)




    def runClean(self, classList):
        cleanCfg = self._config.get("clean")

        if not cleanCfg:
            return

        self._console.info("Cleaning up cache")
        self._console.indent()
        for cleanJob in cleanCfg:
            self._console.info("Job: %s" % cleanJob)

        self._console.outdent()

        self._console.info("Removing cache files:", False)
        self._console.indent()

        for entryPos, entry in enumerate(classes):
            self._console.progress(entryPos, len(classes))
            self._console.debug("Cleaning up: %s" % entry)

            if "tokens" in cleanCache:
                treeutil.cleanTokens(entry)

            if "tree" in cleanCache:
                treeutil.cleanTree(entry)

            if "variants-tree" in cleanCache:
                treeutil.cleanVariantsTree(entry, variants)

            if "compiled" in cleanCache:
                compiler.cleanCompiled(entry, variants, buildProcess)

        self._console.outdent()
        return



    def runApiData(self, classList):
        apiPath = self._config.get("api/path")

        if not apiPath:
            return

        self._apiLoader.storeApi(classList, apiPath)



    def runDependencyDebug(self, partContent, packageContents, variants):
         if not self._config.get("debug/dependencies", False):
            return

         self._console.info("Dependency debugging...")
         self._console.indent()

         for packageId, packageContent in enumerate(packageContents):
             self._console.info("Package %s" % packageId)
             self._console.indent()

             for partId in partContent:
                 if packageId in partContent[partId]:
                     self._console.info("Part %s" % partId)

             for classId in packageContent:
                 self._console.debug("Class: %s" % classId)
                 self._console.indent()

                 for otherClassId in packageContent:
                     otherClassDeps = self._depLoader.getDeps(otherClassId, variants)

                     if classId in otherClassDeps["load"]:
                         self._console.debug("Used by: %s (load)" % otherClassId)

                     if classId in otherClassDeps["run"]:
                         self._console.debug("Used by: %s (run)" % otherClassId)

                 self._console.outdent()
             self._console.outdent()

         self._console.outdent()



    def runLocale(self, partContent, packageContents, variants):
        if not self._config.get("localize"):
            return

        self._console.info("Looking up locales...")
        self._console.indent()

        for packageId, packageContent in enumerate(packageContents):
            self._console.info("Processing package #%s" % packageId)
            self._console.indent()

            po = self._locale.getPoFile(packageContent, variants)
            print po

            self._console.outdent()

        self._console.outdent()





    def runCompiled(self, partContent, packageContents, bootPart, variants):
        if not self._config.get("compile/file"):
            return

        # Read in base file name
        filePath = self._config.get("compile/file")

        # Read in relative file name
        fileUri = self._config.get("compile/uri", filePath)

        # Read in compiler options
        optimize = self._config.get("compile/optimize", [])

        # Whether the code should be formatted
        format = self._config.get("compile/format", False)

        # Read in settings
        settings = self.getSettings()


        # Generating boot script
        self._console.info("Generating boot script...")

        bootBlocks = []
        bootBlocks.append(self.generateSettingsCode(settings, format))
        bootBlocks.append(self.generateVariantsCode(variants, format))
        bootBlocks.append(self.generateCompiledPackageCode(fileUri, partContent, packageContents, bootPart, variants, settings, format))

        if format:
            bootContent = "\n\n".join(bootBlocks)
        else:
            bootContent = util.optimizeJavaScript("".join(bootBlocks))

        # Resolve file name variables
        resolvedFilePath = self._resolveFileName(filePath, variants, settings)

        # Save result file
        filetool.save(resolvedFilePath, bootContent)

        if self._config.get("compile/gzip"):
            filetool.gzip(resolvedFilePath, bootContent)

        self._console.debug("Done: %s" % self._computeContentSize(bootContent))
        self._console.debug("")


        # Generating packages
        self._console.info("Generating packages...")
        self._console.indent()

        for packageId, packageContent in enumerate(packageContents):
            self._console.info("Compiling package #%s:" % packageId, False)
            self._console.indent()

            # Compile file content
            compiledContent = self._treeCompiler.compileClasses(packageContent, variants, optimize, format)

            # Construct file name
            resolvedFilePath = self._resolveFileName(filePath, variants, settings, packageId)

            # Save result file
            filetool.save(resolvedFilePath, compiledContent)

            if self._config.get("compile/gzip"):
                filetool.gzip(resolvedFilePath, compiledContent)

            self._console.debug("Done: %s" % self._computeContentSize(compiledContent))
            self._console.outdent()

        self._console.outdent()




    def runSource(self, partContent, packageContents, bootPart, variants):
        if not self._config.get("source/file"):
            return

        self._console.info("Generate source version...")

        # Read in base file name
        filePath = self._config.get("source/file")

        # Whether the code should be formatted
        format = self._config.get("source/format", False)

        # Read in settings
        settings = self.getSettings()

        # Add data from settings, variants and packages
        sourceBlocks = []
        sourceBlocks.append(self.generateSettingsCode(settings, format))
        sourceBlocks.append(self.generateVariantsCode(variants, format))
        sourceBlocks.append(self.generateSourcePackageCode(partContent, packageContents, bootPart, format))

        if format:
            sourceContent = "\n\n".join(sourceBlocks)
        else:
            sourceContent = util.optimizeJavaScript("".join(sourceBlocks))

        # Construct file name
        resolvedFilePath = self._resolveFileName(filePath, variants, settings)

        # Save result file
        filetool.save(resolvedFilePath, sourceContent)

        if self._config.get("source/gzip"):
            filetool.gzip(resolvedFilePath, sourceContent)

        self._console.debug("Done: %s" % self._computeContentSize(sourceContent))
        self._console.outdent()





    ######################################################################
    #  SETTINGS/VARIANTS/PACKAGE DATA
    ######################################################################

    def getSettings(self):
        settings = {}
        settingsConfig = self._config.get("settings", {})
        settingsRuntime = self._settings

        for key in settingsConfig:
            settings[key] = settingsConfig[key]

        for key in settingsRuntime:
            settings[key] = settingsRuntime[key]

        return settings



    def getVariants(self):
        variants = {}
        variantsConfig = self._config.get("variants", {})
        variantsRuntime = self._variants

        for key in variantsConfig:
            variants[key] = variantsConfig[key]

        for key in variantsRuntime:
            variants[key] = [variantsRuntime[key]]

        return variants


    def _toJavaScript(self, value):
        number = re.compile("^([0-9\-]+)$")

        if not (value == "false" or value == "true" or value == "null" or number.match(value)):
            value = '"%s"' % value.replace("\"", "\\\"")

        return value


    def generateSettingsCode(self, settings, format=False):
        result = 'if(!window.qxsettings)qxsettings={};'

        for key in settings:
            if format:
                result += "\n"

            value = self._toJavaScript(settings[key])
            result += 'qxsettings["%s"]=%s;' % (key, value)

        return result



    def generateVariantsCode(self, variants, format=False):
        result = 'if(!window.qxvariants)qxvariants={};'

        for key in variants:
            if format:
                result += "\n"

            value = self._toJavaScript(variants[key])
            result += 'qxvariants["%s"]=%s;' % (key, value)

        return result



    def generateSourcePackageCode(self, partContent, packageContents, bootPart, format=False):
        if not partContent:
            return ""

        # Translate part information to JavaScript
        partData = "{"
        for partId in partContent:
            partData += '"%s":' % (partId)
            partData += ('%s,' % partContent[partId]).replace(" ", "")

        partData=partData[:-1] + "}"

        # Translate URI data to JavaScript
        allUris = []
        for packageId, packageContent in enumerate(packageContents):
            packageUris = []
            for fileId in packageContent:
                packageUris.append('"%s"' % self._classes[fileId]["uri"])

            allUris.append("[" + ",".join(packageUris) + "]")

        uriData = "[" + ",\n".join(allUris) + "]"

        # Locate and load loader basic script
        loaderFile = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "loader.js")
        result = filetool.read(loaderFile)

        # Replace template with computed data
        result = result.replace("%PARTS%", partData)
        result = result.replace("%URIS%", uriData)
        result = result.replace("%BOOT%", '"%s"' % bootPart)

        return result



    def generateCompiledPackageCode(self, fileName, partContent, packageContents, bootPart, variants, settings, format=False):
        if not partContent:
            return ""

        # Translate part information to JavaScript
        partData = "{"
        for partId in partContent:
            partData += '"%s":' % (partId)
            partData += ('%s,' % partContent[partId]).replace(" ", "")

        partData=partData[:-1] + "}"

        # Translate URI data to JavaScript
        allUris = []
        for packageId, packageContent in enumerate(packageContents):
            packageFileName = self._resolveFileName(fileName, variants, settings, packageId)
            allUris.append('["' + packageFileName + '"]')

        uriData = "[" + ",\n".join(allUris) + "]"

        # Locate and load loader basic script
        loaderFile = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "loader.js")
        result = filetool.read(loaderFile)

        # Replace template with computed data
        result = result.replace("%PARTS%", partData)
        result = result.replace("%URIS%", uriData)
        result = result.replace("%BOOT%", '"%s"' % bootPart)

        return result







    ######################################################################
    #  DEPENDENCIES
    ######################################################################

    def getIncludes(self):
        includeCfg = self._config.get("include", [])

        # Splitting lists
        self._console.debug("Preparing include configuration...")
        smartInclude, explicitInclude = self._splitIncludeExcludeList(includeCfg)
        self._console.indent()

        if len(smartInclude) > 0 or len(explicitInclude) > 0:
            # Configuration feedback
            self._console.debug("Including %s items smart, %s items explicit" % (len(smartInclude), len(explicitInclude)))

            if len(explicitInclude) > 0:
                self._console.warn("Explicit included classes may not work")

            # Resolve regexps
            self._console.debug("Expanding expressions...")
            smartInclude = self._expandRegExps(smartInclude)
            explicitInclude = self._expandRegExps(explicitInclude)

        elif self._config.get("packages"):
            # Special part include handling
            self._console.info("Including part classes...")
            partsCfg = partsCfg = self._config.get("packages/parts", {})
            smartInclude = []
            for partId in partsCfg:
                smartInclude.extend(partsCfg[partId])

            # Configuration feedback
            self._console.debug("Including %s items smart, %s items explicit" % (len(smartInclude), len(explicitInclude)))

            # Resolve regexps
            self._console.debug("Expanding expressions...")
            smartInclude = self._expandRegExps(smartInclude)

        self._console.outdent()

        return smartInclude, explicitInclude



    def getExcludes(self):
        excludeCfg = self._config.get("exclude", [])

        # Splitting lists
        self._console.debug("Preparing exclude configuration...")
        smartExclude, explicitExclude = self._splitIncludeExcludeList(excludeCfg)

        # Configuration feedback
        self._console.indent()
        self._console.debug("Excluding %s items smart, %s items explicit" % (len(smartExclude), len(explicitExclude)))

        if len(excludeCfg) > 0:
            self._console.warn("Excludes may break code!")

        self._console.outdent()

        # Resolve regexps
        self._console.indent()
        self._console.debug("Expanding expressions...")
        smartExclude = self._expandRegExps(smartExclude)
        explicitExclude = self._expandRegExps(explicitExclude)
        self._console.outdent()

        return smartExclude, explicitExclude



    def _splitIncludeExcludeList(self, data):
        intelli = []
        explicit = []

        for entry in data:
            if entry[0] == "=":
                explicit.append(entry[1:])
            else:
                intelli.append(entry)

        return intelli, explicit



    def _expandRegExps(self, entries):
        result = []

        for entry in entries:
            # Fast path: Try if a matching class could directly be found
            if entry in self._classes:
                result.append(entry)

            else:
                regexp = textutil.toRegExp(entry)
                expanded = []

                for classId in self._classes:
                    if regexp.search(classId):
                        if not classId in expanded:
                            expanded.append(classId)

                if len(expanded) == 0:
                    self._console.error("Expression gives no results. Malformed entry: %s" % entry)
                    sys.exit(1)

                result.extend(expanded)

        return result



    def _resolveFileName(self, fileName, variants=None, settings=None, packageId=""):
        if variants:
            for key in variants:
                pattern = "{%s}" % key
                fileName = fileName.replace(pattern, variants[key])

        if settings:
            for key in settings:
                pattern = "{%s}" % key
                fileName = fileName.replace(pattern, settings[key])

        if packageId != "":
            fileName = fileName.replace(".js", "-%s.js" % packageId)

        return fileName


    def _computeContentSize(self, content):
        # Convert to utf-8 first
        uni = unicode(content).encode("utf-8")

        # Calculate sizes
        origSize = len(uni) / 1024
        compressedSize = len(zlib.compress(uni, 9)) / 1024

        return "%sKB / %sKB" % (origSize, compressedSize)
