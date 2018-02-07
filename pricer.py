from __future__ import print_function
import sys
import os
import math

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic

import QuantLib as ql


directory = os.path.dirname(os.path.abspath(__file__))
qtCreatorFile = os.path.join(directory, "pricer.ui")
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

day_count = ql.Thirty360()
calendar = ql.UnitedStates()

def simplederivative(option, var, dvarperc = 0.01):
    var0 = var.value()
    h = var0 * dvarperc
    var.setValue(var0 + h)
    P_plus = option.NPV()
    var.setValue(var0 - h)
    P_minus = option.NPV()
    var.setValue(var0)
    return (P_plus - P_minus) / 2. / h

def simplesecondderivative(option, var, dvarperc = 0.01):
    var0 = var.value()
    P0 = option.NPV()
    h = var0 * dvarperc
    var.setValue(var0 + h)
    P_plus = option.NPV()
    var.setValue(var0 - h)
    P_minus = option.NPV()
    var.setValue(var0)
    return (P_plus + P_minus - 2. * P0) / h / h

def computegreeks(results, option, spot, volatility, rf, today):
    if math.isnan(results["delta"]):
        results["delta"] = simplederivative(option, spot)

    if math.isnan(results["gamma"]):
        results["gamma"] = simplesecondderivative(option, spot)
        
    if math.isnan(results["rho"]):
        results["rho"] = simplederivative(option, rf)
        
    if math.isnan(results["vega"]):
        results["vega"] = simplederivative(option, volatility)

    if math.isnan(results["theta"]):
        P0 = option.NPV()
        ql.Settings.instance().evaluationDate = today + 1
        P1 = option.NPV()
        h = 1./365.
        results["theta"] = (P1 - P0) / h
        ql.Settings.instance().evaluationDate = today

def OptionCalc(options):
    print(options)
    spot = ql.SimpleQuote(options["spot"])
    strike = options["strike"]
    volatility = ql.SimpleQuote(options["volatility"])
    maturity = options["maturity"]
    rf = ql.SimpleQuote(options["rf"])
    optionType = options["optionType"]
    pricingEngine = options["pricingEngine"]
    optionExercise = options["optionExercise"]

    if not hasattr(ql.Option, optionType):
        raise Exception("option type not understood")
    optionType = getattr(ql.Option, optionType)

    today = ql.Settings.instance().evaluationDate
    maturity_date = today + int(maturity)

    divYield = 0.
    rebate = 0.

    # process = ql.BlackScholesMertonProcess(
    #     ql.QuoteHandle(spot),
    #     ql.YieldTermStructureHandle(ql.FlatForward(today, divYield, day_count)),
    #     ql.YieldTermStructureHandle(ql.FlatForward(today, ql.QuoteHandle(rf), day_count)),
    #     ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, ql.QuoteHandle(volatility), day_count)))

    process = ql.BlackScholesProcess(
        ql.QuoteHandle(spot),
        ql.YieldTermStructureHandle(ql.FlatForward(today, ql.QuoteHandle(rf), day_count)),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, ql.QuoteHandle(volatility), day_count)))

    if (optionExercise == "European"):
        optionExercise = ql.EuropeanExercise(maturity_date)
    elif (optionExercise == "American"):
        optionExercise = ql.AmericanExercise(today + 1, maturity_date)
    else:
        raise Exception("optionExercise not understood")


    if (pricingEngine == "Analytical"):
        pricingEngine = ql.AnalyticEuropeanEngine(process)
    elif (pricingEngine == "AnalyticalBinary"):
        pricingEngine = ql.AnalyticBinaryBarrierEngine(process)
    elif (pricingEngine == "FD"):
        pricingEngine = ql.FdBlackScholesBarrierEngine(process, timeSteps, gridPoints)
    elif (pricingEngine == "MC"):
        pricingEngine = ql.MCBarrierEngine(process, 'pseudorandom', timeSteps=1, requiredTolerance=0.02, seed=42)
    elif (pricingEngine == "Binomial"):
        pricingEngine = ql.BinomialBarrierEngine(process, 'jr', timeSteps)
    else:
        raise Exception("pricingEngine not understood")

    option = ql.VanillaOption(ql.PlainVanillaPayoff(optionType, strike),
                              optionExercise)

    option.setPricingEngine(pricingEngine)

    results = {}
    for t in ["NPV", "delta", "vega", "theta", "rho", "gamma"]:
        try:
            results[t] = getattr(option, t)()
        except RuntimeError as e:
            print(t, e)
            results[t] = float('nan')

    if math.isnan(results["NPV"]):
        return results
    computegreeks(results, option, spot, volatility, rf, today)
    return results



def BarrierOptionCalc(options):
    print(options)
    spot = ql.SimpleQuote(options["spot"])
    strike = options["strike"]
    barrier = options["barrier"]
    barrierType = options["barrierType"]
    volatility = ql.SimpleQuote(options["volatility"])
    maturity = options["maturity"]
    rf = ql.SimpleQuote(options["rf"])
    optionType = options["optionType"]
    pricingEngine = options["pricingEngine"]
    optionExercise = options["optionExercise"]
    
    if not hasattr(ql.Barrier, barrierType):
        raise Exception("barrier type not understood")
    barrierType = getattr(ql.Barrier, barrierType)

    
    if not hasattr(ql.Option, optionType):
        raise Exception("option type not understood")
    optionType = getattr(ql.Option, optionType)


    today = ql.Settings.instance().evaluationDate
    maturity_date = today + int(maturity)

    divYield = 0.
    rebate = 0.

    # process = ql.BlackScholesMertonProcess(
    #     ql.QuoteHandle(spot),
    #     ql.YieldTermStructureHandle(ql.FlatForward(today, divYield, day_count)),
    #     ql.YieldTermStructureHandle(ql.FlatForward(today, ql.QuoteHandle(rf), day_count)),
    #     ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, ql.QuoteHandle(volatility), day_count)))

    process = ql.BlackScholesProcess(
        ql.QuoteHandle(spot),
        ql.YieldTermStructureHandle(ql.FlatForward(today, ql.QuoteHandle(rf), day_count)),
        ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, ql.QuoteHandle(volatility), day_count)))
    
    if (optionExercise == "European"):
        optionExercise = ql.EuropeanExercise(maturity_date)
    elif (optionExercise == "American"):
        optionExercise = ql.AmericanExercise(today + 1, maturity_date)
    else:
        raise Exception("optionExercise not understood")

    timeSteps = 1000
    gridPoints = 1000
    
    if (pricingEngine == "Analytical"):
        pricingEngine = ql.AnalyticBarrierEngine(process)
    elif (pricingEngine == "AnalyticalBinary"):
        pricingEngine = ql.AnalyticBinaryBarrierEngine(process)
    elif (pricingEngine == "FD"):
        pricingEngine = ql.FdBlackScholesBarrierEngine(process, timeSteps, gridPoints)
    elif (pricingEngine == "MC"):
        pricingEngine = ql.MCBarrierEngine(process, 'pseudorandom', timeSteps=1, requiredTolerance=0.02, seed=42)
    elif (pricingEngine == "Binomial"):
        pricingEngine = ql.BinomialBarrierEngine(process, 'jr', timeSteps)
    else:
        raise Exception("pricingEngine not understood")

    option = ql.BarrierOption(barrierType, barrier, rebate,
                              ql.PlainVanillaPayoff(optionType, strike),
                              optionExercise)

    option.setPricingEngine(pricingEngine)


    results = {}
    for t in ["NPV", "delta", "vega", "theta", "rho", "gamma"]:
        try:
            results[t] = getattr(option, t)()
        except RuntimeError as e:
            print(t, e)
            results[t] = float('nan')

    if math.isnan(results["NPV"]):
        return results
    computegreeks(results, option, spot, volatility, rf, today)
    return results


class BarrierOptionCalcThread(QThread):
    def __init__(self, options, dataready):
        super(BarrierOptionCalcThread, self).__init__()
        self.options = options
        self.dataready = dataready
        
    def run(self):
        results = BarrierOptionCalc(self.options)
        self.dataready.emit(results)


class MyApp(QMainWindow, Ui_MainWindow):
    dataready = pyqtSignal(object)
    
    def __init__(self, app):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.app = app
        
        self.setupUi(self)
        self.CalculateButton.clicked.connect(self.CalculateOption)

        self.DownOut_PushButton.clicked.connect(lambda: self.examplesetup("DownOut"))
        self.DownIn_PushButton.clicked.connect(lambda: self.examplesetup("DownIn"))
        self.UpOut_PushButton.clicked.connect(lambda: self.examplesetup("UpOut"))
        self.UpIn_PushButton.clicked.connect(lambda: self.examplesetup("UpIn"))

        print(self.optionType_listWidget.currentRow())

        for i in range(0, 6):
            item = self.results_tableWidget.item(i,0)
            item.setFlags(item.flags() ^  Qt.ItemIsEditable)

        self.dataready.connect(self.done)


    def examplesetup(self, t):
        if t == "DownOut":
            strike = 90
            barrier = 80
            pos = 1
        elif t == "DownIn":
            strike = 80
            barrier = 90
            pos = 3
        elif t == "UpOut":
            strike = 110
            barrier = 120
            pos = 0
        elif t == "UpIn":
            strike = 120
            barrier = 130
            pos = 2
                        
        self.inputs_tableWidget.item(1,0).setText(str(strike))
        self.inputs_tableWidget.item(2,0).setText(str(barrier))
        self.barrierType_listWidget.setCurrentItem(self.barrierType_listWidget.item(pos))


    def CalculateOption(self):
        options = {}
        options["spot"] = float(self.inputs_tableWidget.item(0,0).text())
        options["strike"] = float(self.inputs_tableWidget.item(1,0).text())
        try:
            options["barrier"] = float(self.inputs_tableWidget.item(2,0).text())
            options["barrierType"] = str(self.barrierType_listWidget.selectedItems()[0].text())
        except:
            options["barrier"] = None
            
        options["volatility"] = float(self.inputs_tableWidget.item(3,0).text())/100.
        options["maturity"] = int(self.inputs_tableWidget.item(4,0).text())
        options["rf"] = float(self.inputs_tableWidget.item(5,0).text())/100.
        options["optionType"] = str(self.optionType_listWidget.selectedItems()[0].text())
        options["optionExercise"] = str(self.optionExercise_listWidget.selectedItems()[0].text())
        options["pricingEngine"] = str(self.pricingEngine_listWidget.selectedItems()[0].text())

        self.CalculateButton.setText("Calculating...")
        self.CalculateButton.setEnabled(False)
        self.inputs_tableWidget.setEnabled(False)
        self.barrierType_listWidget.setEnabled(False)
        self.optionType_listWidget.setEnabled(False)
        self.app.processEvents()
        
        usemp = False
        if usemp:
            from multiprocessing import Pool
            p = Pool(1)
            r = p.apply_async(BarrierOptionCalc, args=(options,))
            self.done(r.get())
            return
        
        usethread = False
        if usethread:
            self.get_thread = BarrierOptionCalcThread(options, self.dataready)
            self.get_thread.start()
            return

        if options["barrier"] is not None:
            self.done(BarrierOptionCalc(options))
        else:
            self.done(OptionCalc(options))

    def done(self, results):
        self.results_tableWidget.item(0,0).setText("%.3f" % results["NPV"])
        self.results_tableWidget.item(1,0).setText("%.3f" % results["delta"])
        self.results_tableWidget.item(2,0).setText("%.3f" % results["vega"])
        self.results_tableWidget.item(3,0).setText("%.3f" % results["theta"])
        self.results_tableWidget.item(4,0).setText("%.3f" % results["rho"])
        self.results_tableWidget.item(5,0).setText("%.3f" % results["gamma"])
        
        self.CalculateButton.setEnabled(True)
        self.CalculateButton.setText("Calculate")
        self.inputs_tableWidget.setEnabled(True)
        self.barrierType_listWidget.setEnabled(True)
        self.optionType_listWidget.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp(app)
    window.show()
    sys.exit(app.exec_())
