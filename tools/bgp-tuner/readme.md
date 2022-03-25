# BGPTuner: User Interface for anycast management
### SAND/PAADDOS anycast management Interface (GUI)

SAND/PAADDOS anycast management Interface (GUI)

## DESCRIPTION:
    BGP ANYCAST TUNER is a prototype graphical interface that provides a simple 
    and intuitive interface for operators and presents the distribution of clients 
    over the anycast sites for the different pre-determined BGP configurations 
    from the BGP Anycast Playbook.
    
    The interface shows the client distribution for each site using a histogram, 
    and sliders underneath the histogram. 
    
    Using these sliders, operators can increase or decrease the catchment of a site 
    using a set of predetermined settings indicated by “notches” on the slider. 
    These notches correspond to specific BGP policies, the effect on catchment.

## LIMITATIONS:
    This version is prepared for anycast sites: CDG, IAD, LHR, MIA, POA, SYD.
    Drop down menu is not fully operational.
    
## REQUIREMENTS:
    To run this notebook, it's necessary to previously build the BGP anycast playbook.
    For convenience, we provide some BGP playbook samples in the dataset directory.

    ```
	./dataset:
	fake.csv
	prepend+withdraw-dataframe.csv
	prepend-only-dataframe.csv
	prepend-only-dataframe_percent.csv
	```

    To run the GUI interface first install the python requirements (look at INSTALL.TXT) 
    on anygility package base directory and 
    run bgp-tuner.py

    Then access the interface just open your browser on http://127.0.0.1:12345/ 
    as indicated by the program output.

## USAGE:
    pip install -r ./../../pyreqs/bgptuner-requirements.txt 
    cd bgp-tuner
    ./bgp-tuner.py
    
## CONTACT: leandro.bertholdo@gmail.com and ceron@botlog.org
