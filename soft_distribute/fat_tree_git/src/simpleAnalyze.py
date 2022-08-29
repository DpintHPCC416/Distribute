def analyze2(valueList):
    all = {}
    for value in valueList:
        hop = value[0]
        task = value[1]
        interval = value[2]
        if hop in all.keys():
            all[hop][0] = all[hop][0] + interval
            all[hop][1] = all[hop][1] + 1
        else:
            all[hop] = [interval, 1]
    result = [0 for i in range(0,len(all.keys()) + 1)]
    for key in all.keys():
        result[key] = float(all[key][0]) / all[key][1]
    print result

with open("../result/10.0.0.2") as f:
    valueList = []
    while True:
        line = f.readline()
        if line == '':
            break
        args = line.split(',')
        hop = int(args[3])
        task = int(args[4])
        value = long(args[5], base=16)
        if task == 2:
            valueList.append((hop, task, value))
    analyze2(valueList)
