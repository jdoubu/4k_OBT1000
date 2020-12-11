# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsVectorLayer,
                       QgsField,
                       QgsFields,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsValueMapFieldFormatter,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFeatureSink)
from qgis import processing
import csv


class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OZINPUT = 'OZINPUT'
    INPUT = 'INPUT'
    UPDATE = 'UPDATE'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'myscript'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('My Script')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Example scripts')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'examplescripts'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Example algorithm short description")
        
    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading | QgsProcessingAlgorithm.FlagDeprecated

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(QgsProcessingParameterFeatureSource(self.OZINPUT, self.tr('Input 4k OZ layer'), [QgsProcessing.TypeVectorAnyGeometry], None, False))
        self.addParameter(QgsProcessingParameterFile(self.INPUT, self.tr('Input BPI layer'), extension='csv'))
        self.addParameter(QgsProcessingParameterFile(self.UPDATE, self.tr('Update OBT layer'), extension='csv'))
        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr('Output layer')))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        ozsource = self.parameterAsSource(parameters, self.OZINPUT, context)
        ozlayer = self.parameterAsVectorLayer(parameters, self.OZINPUT, context)
        source = self.parameterAsFile(parameters, self.INPUT, context)
        update = self.parameterAsFile(parameters, self.UPDATE, context)
        
        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
            
        fieldnames = [field.name() for field in ozsource.fields()]
        total = 100.0 / ozsource.featureCount() if ozsource.featureCount() else 0
            
        with open(source) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            olddata = [i for i in reader]
            roldata = sorted(list(i['ROL'] for i in olddata))                   # list with language codes (within the BPI dataset)
            ulcode_source = sorted(list(set(i['ROL'] for i in olddata)))        # list with unique language codes (within the BPI dataset)
            #oz_list = sorted(list(set([i['WorldID'] for i in olddata)))        # list with the unique omega zone identifiers (within the BPI dataset)
            oz_list = sorted(list(set(i['OmegaZone'] for i in olddata)))
            oz_dict = {i['WorldID']:i['OmegaZone'] for i in olddata}
            oz_country_dict = {i['WorldID']:i['Cnty_Name'] for i in olddata}
            cname = sorted(list(set(i['Cnty_Name'] for i in olddata)))
            
        oz_lang_dict = {}
        with open(source) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                item = oz_lang_dict.get(row['OmegaZone'], list())
                item.append(row['ROL'])
                oz_lang_dict[row['OmegaZone']] = item
                
        lcode_dict = {i:0 for i in ulcode_source}
        for i in roldata:
            if i in ulcode_source:
                lcode_dict[i] += 1                                             
            
        with open(update) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            data = [i for i in reader]
            countries = sorted(list(set(i['Country'] for i in data)))
            lcode_update = sorted(list(set(i['Language Code'] for i in data)))
            lang_pop_dict = {i['Language Code']:i['Population'] for i in data}
            lang_lang_dict = {i['Language Code']:i['Language Name'] for i in data}
            lang_egids_dict = {i['Language Code']:i['EGIDS Group'] for i in data}
            lang_color_dict = {i['Language Code']:i['Color'] for i in data}
        
        ndict = {}
        for lang, pop in lang_pop_dict.items():
            ndict[lang] = int(pop.replace('.', ''))

        oz_update = []
        ozlang_update = {i:[] for i in oz_list}
        ozlan_update = {i:0 for i in oz_list}
        for oz, lang in oz_lang_dict.items():
            for i in lang:
                if i in lcode_update:
                    oz_update.append(oz)
                    ozlang_update[oz].append(i)
                    ozlan_update[oz] += ndict[i] / lcode_dict[i]
        
        ozset_update = sorted(list(set(oz_update)))
                    
        # Send some information to the user
        desdict = dict(sorted(ozlan_update.items(), key=lambda item: item[1], reverse=True))
        #feedback.pushInfo('{}'.format(desdict))
        
        lcode_output = []
        nlcode_dict = {i:0 for i in lcode_update}
        for i in roldata: 
            if i in lcode_update: 
                lcode_output.append(i)
                nlcode_dict[i] += 1
        
        nolang = []
        for key, value in nlcode_dict.items():
            if value == 0:
                nolang.append(key)
        
        crs = ozlayer.crs().authid()
        temp = QgsVectorLayer('Polygon?crs='+crs, 'temp', 'memory')
        pr = temp.dataProvider()
        pr.addAttributes([QgsField("OBJECTID_1", QVariant.Int), 
                          QgsField("OBJECTID", QVariant.Int),  
                          QgsField("OZ ID", QVariant.String),
                          QgsField("Omega Zone", QVariant.String), 
                          QgsField("World ABC", QVariant.String),
                          QgsField("Province", QVariant.String),
                          QgsField("Country", QVariant.String),
                          QgsField("Region", QVariant.String),
                          QgsField("Population", QVariant.Double),
                          QgsField("Number UBL", QVariant.Int),
                          QgsField("Population UBL", QVariant.Int),
                          QgsField("Perc_Pop UBL", QVariant.Double),
                          QgsField("Language Details", QVariant.String),
                          QgsField("Color", QVariant.String)
                          ])
        temp.updateFields()
        
        fieldsout = QgsFields()
        fieldsout.append(QgsField("OBJECTID_1", QVariant.Int))
        fieldsout.append(QgsField("OBJECTID", QVariant.Int))
        fieldsout.append(QgsField('OZ ID',QVariant.String))
        fieldsout.append(QgsField('Omega Zone',QVariant.String))
        fieldsout.append(QgsField("World ABC", QVariant.String))
        fieldsout.append(QgsField("Province", QVariant.String))
        fieldsout.append(QgsField("Country", QVariant.String))
        fieldsout.append(QgsField("Region", QVariant.String))
        fieldsout.append(QgsField('Population',QVariant.Double))
        fieldsout.append(QgsField('Number UBL',QVariant.Int))
        fieldsout.append(QgsField('Population UBL',QVariant.Int))
        fieldsout.append(QgsField('Perc_Pop UBL',QVariant.Double))
        fieldsout.append(QgsField('Language Details',QVariant.String))
        fieldsout.append(QgsField('Color',QVariant.String))
        
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fieldsout,#temp.fields(),
            ozsource.wkbType(),
            ozsource.sourceCrs()
        )
        
        lang_tpop_dict = {i:0 for i in lcode_update}
        for feat in ozlayer.getFeatures():
            f = QgsFeature()
            f.setGeometry(feat.geometry())
            f.setFields(fieldsout)
            f["OBJECTID_1"] = feat["OBJECTID_1"]
            f["OBJECTID"] = feat["OBJECTID"]
            f["OZ ID"] = feat["WorldID"]
            f["Omega Zone"] = feat["Zone_Name"]
            f["World ABC"] = feat["World"]
            f["Province"] = feat["Adm1_Name"]
            f["Country"] = feat["Cnty_Name"]
            f["Region"] = feat["RegionYWAM"]
            f["Population"] = feat["Population"]
            f["Number UBL"] = 0
            f["Population UBL"] = 0
            f["Perc_Pop UBL"] = 0
            f["Language Details"] = ""
            f["Color"] = ""
            color = 0
            if f["Omega Zone"] in ozset_update:
                for i in ozlang_update[f["Omega Zone"]]:
                    f["Number UBL"] += 1
                    lang_tpop_dict[i] += f["Population"]
                    color = int(lang_color_dict[i])
                    if color > 0:
                        f["Color"] = f["Country"]
            pr.addFeature(f)
        temp.updateExtents()
        
        temp.startEditing()
        for feat in temp.getFeatures():
            pop_noOBT_oz= 0
            lpe_string = ""
            if feat["Omega Zone"] in ozset_update:
                langpop = {i:0 for i in ozlang_update[feat["Omega Zone"]]}
                for i in ozlang_update[feat["Omega Zone"]]:
                    try:
                        ppopoz_lang = feat["Population"] / lang_tpop_dict[i]
                        pop_noOBT_oz += ndict[i] * ppopoz_lang                
                        pop_lang_oz = int(ndict[i] * ppopoz_lang)
                        langpop[i] = pop_lang_oz
                    except ZeroDivisionError:
                        pass
                sdict = dict(sorted(langpop.items(), key=lambda item: item[1], reverse=True))        
                n = 0
                for key, value in sdict.items():
                    n += 1
                    if feat["Language Details"] == "":
                        feat["Language Details"] += lang_lang_dict[key] + ";" + str(value) + ";" + lang_egids_dict[key]
                    else:
                        feat["Language Details"] += ";" + lang_lang_dict[key] + ";" + str(value) + ";" + lang_egids_dict[key]
                if pop_noOBT_oz > 0:
                    feat["Population UBL"] = round(pop_noOBT_oz, 0)
                    feat["Perc_Pop UBL"] = round(pop_noOBT_oz / feat["Population"] * 100, 1)
            temp.updateFeature(feat)
        temp.commitChanges()
        
        sec_countries = ()
            
        for feat in temp.getFeatures():
            if feat["Country"] in sec_countries:
                feat["Number UBL"] = None
                feat["Population UBL"] = None
                feat["Perc_Pop UBL"] = None
                feat["Language Details"] = None
                feat["Color"] = None
            sink.addFeature(feat, QgsFeatureSink.FastInsert)
        
        return {}

