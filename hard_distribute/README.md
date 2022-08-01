### Introduction
Code of distribute sketch experiment code on tofino switch, including control plane code and flow table distribution.
### Contents
`distribute.p4`:P4-16 code of control plane  
`common`:headers and utils used in this experiment  
`util`:controller for distributing flow table
### How to use
1.install and configure the required environment(SDE and path)  

2.compilation and installation distribute.py in tofino switch(version 9.7.2)  

3.set swtich ports  

4.run util.controller.py with python3，also need to modify this code according to your topology and control strategy
